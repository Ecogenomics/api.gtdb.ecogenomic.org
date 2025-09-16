from typing import List

import numpy as np
import sqlmodel as sm
from sqlalchemy import func, union_all
from sqlmodel import Session

from api.config import GTDB_RELEASES, CURRENT_RELEASE
from api.db.gtdb import DbGtdbSpeciesClusterCount, DbMetadataTaxonomy, DbGenomes, DbMetadataNucleotide, DbMetadataNcbi
from api.db.gtdb_web import DbGtdbTree, DbGtdbTreeUrlBergeys, DbGtdbTreeUrlSeqCode, DbGtdbTreeUrlNcbi, DbGtdbTreeUrlLpsn, \
    DbGtdbTreeUrlSandpiper, DbGtdbTreeChildren, DbTaxonHist
from api.exceptions import HttpBadRequest, HttpNotFound, HttpInternalServerError
from api.model.graph import GraphHistogramBin
from api.model.taxon import TaxonDescendants, TaxonSearchResponse, TaxonPreviousReleases, TaxonCard, \
    TaxonPreviousReleasesPaginated, TaxonGenomesDetailResponse, TaxonGenomesDetailRow


def get_taxon_descendants(taxon: str, db: Session) -> List[TaxonDescendants]:
    """Returns the direct descendants below this taxon."""

    # Get parent info
    taxon_query = sm.select(DbGtdbTree).where(DbGtdbTree.taxon == taxon)
    taxon_results = db.exec(taxon_query).all()

    if len(taxon_results) == 0:
        raise HttpBadRequest(f'The taxon {taxon} does not exist.')
    if len(taxon_results) > 1:
        raise HttpInternalServerError(f'The taxon {taxon} exists multiple times, please report this issue.')
    parent_id = taxon_results[0].id

    query = (
        sm.select(
            DbGtdbTree.taxon,
            DbGtdbTree.total,
            DbGtdbTree.type,
            DbGtdbTree.is_rep,
            DbGtdbTree.type_material,
            DbGtdbTree.n_desc_children,
            DbGtdbTreeUrlBergeys.url.label('bergeys_url'),
            DbGtdbTreeUrlSeqCode.url.label('seqcode_url'),
            DbGtdbTreeUrlLpsn.url.label('lpsn_url'),
            DbGtdbTreeUrlNcbi.taxid.label('ncbi_taxid'),
            DbGtdbTreeUrlSandpiper.url.label('sandpiper_url')
        )
        .join(DbGtdbTreeChildren, DbGtdbTreeChildren.child_id == DbGtdbTree.id)
        .outerjoin(DbGtdbTreeUrlBergeys, DbGtdbTreeUrlBergeys.id == DbGtdbTree.id)
        .outerjoin(DbGtdbTreeUrlSeqCode, DbGtdbTreeUrlSeqCode.id == DbGtdbTree.id)
        .outerjoin(DbGtdbTreeUrlLpsn, DbGtdbTreeUrlLpsn.id == DbGtdbTree.id)
        .outerjoin(DbGtdbTreeUrlNcbi, DbGtdbTreeUrlNcbi.id == DbGtdbTree.id)
        .outerjoin(DbGtdbTreeUrlSandpiper, DbGtdbTreeUrlSandpiper.id == DbGtdbTree.id)
        .where(DbGtdbTreeChildren.parent_id == parent_id)
        .order_by(DbGtdbTreeChildren.order_id)
    )

    results = db.exec(query).all()

    out = list()
    for result in results:
        out.append(
            TaxonDescendants(
                taxon=result.taxon,
                total=result.total,
                isGenome=result.type == 'genome',
                isRep=result.is_rep,
                typeMaterial=result.type_material,
                nDescChildren=result.n_desc_children,
                bergeysUrl=result.bergeys_url,
                seqcodeUrl=result.seqcode_url,
                lpsnUrl=result.lpsn_url,
                ncbiTaxId=result.ncbi_taxid,
                sandpiperUrl=result.sandpiper_url
            )
        )
    return out


def search_for_taxon(taxon: str, limit: int | None, db: Session) -> TaxonSearchResponse:
    # Maximum number of results to be returned
    if limit is not None:
        limit = min(limit, 100)
    else:
        limit = 100

    if taxon.startswith('d__'):
        col = DbGtdbSpeciesClusterCount.gtdb_domain
        prefix = 'd__'
    elif taxon.startswith('p__'):
        col = DbGtdbSpeciesClusterCount.gtdb_phylum
        prefix = 'p__'
    elif taxon.startswith('c__'):
        col = DbGtdbSpeciesClusterCount.gtdb_class
        prefix = 'c__'
    elif taxon.startswith('o__'):
        col = DbGtdbSpeciesClusterCount.gtdb_order
        prefix = 'o__'
    elif taxon.startswith('f__'):
        col = DbGtdbSpeciesClusterCount.gtdb_family
        prefix = 'f__'
    elif taxon.startswith('g__'):
        col = DbGtdbSpeciesClusterCount.gtdb_genus
        prefix = 'g__'
    elif taxon.startswith('s__'):
        col = DbGtdbSpeciesClusterCount.gtdb_species
        prefix = 's__'
    else:
        col = None
        prefix = None

    # If a prefix has been supplied, then we can just search that rank only
    if col:
        query = sm.select(func.concat(prefix, col)).where(col.ilike(f'{taxon[3:]}%')).distinct().limit(limit)
        results = db.exec(query).all()
        return TaxonSearchResponse(matches=list(results))

    # Run against all columns
    else:
        # Create a subquery for each rank
        subqueries = list()
        for col, prefix in (
                (DbGtdbSpeciesClusterCount.gtdb_domain, 'd__'),
                (DbGtdbSpeciesClusterCount.gtdb_phylum, 'p__'),
                (DbGtdbSpeciesClusterCount.gtdb_class, 'c__'),
                (DbGtdbSpeciesClusterCount.gtdb_order, 'o__'),
                (DbGtdbSpeciesClusterCount.gtdb_family, 'f__'),
                (DbGtdbSpeciesClusterCount.gtdb_genus, 'g__'),
                (DbGtdbSpeciesClusterCount.gtdb_species, 's__')
        ):
            subquery = (
                sm.select(func.concat(prefix, col))
                .where(col.ilike(f'%{taxon}%'))
                .distinct()
                .limit(limit)
            )
            subqueries.append(subquery)

        # Union the subqueries and run them
        query = union_all(*subqueries)
        results = db.exec(query).all()
        return TaxonSearchResponse(matches=[x[0] for x in results])


def get_taxon_genomes_in_taxon(taxon: str, sp_reps_only: bool | None, db: Session) -> List[str]:
    rank_to_col = {
        'd__': DbMetadataTaxonomy.gtdb_domain,
        'p__': DbMetadataTaxonomy.gtdb_phylum,
        'c__': DbMetadataTaxonomy.gtdb_class,
        'o__': DbMetadataTaxonomy.gtdb_order,
        'f__': DbMetadataTaxonomy.gtdb_family,
        'g__': DbMetadataTaxonomy.gtdb_genus,
        's__': DbMetadataTaxonomy.gtdb_species
    }
    col = rank_to_col.get(taxon[0:3])
    if not col:
        raise HttpBadRequest('Taxon must be in green-genes format, e.g. "g__Foo"')

    # Create the query
    query = (
        sm.select(DbGenomes.name)
        .join(DbMetadataTaxonomy, DbMetadataTaxonomy.id == DbGenomes.id)
        .where(col == taxon)
        .order_by(DbGenomes.name)
    )

    # Optionally, limit to only those that are representatives
    if sp_reps_only:
        query = query.where(DbMetadataTaxonomy.gtdb_representative == True)

    results = db.exec(query).all()
    return list(results)


def search_for_taxon_all_releases(taxon: str, limit: int | None, db: Session) -> TaxonSearchResponse:
    # Maximum number of results to be returned
    if limit:
        limit = min(limit, 100)
    else:
        limit = 100

    if taxon.startswith('d__'):
        col = DbTaxonHist.rank_domain
    elif taxon.startswith('p__'):
        col = DbTaxonHist.rank_phylum
    elif taxon.startswith('c__'):
        col = DbTaxonHist.rank_class
    elif taxon.startswith('o__'):
        col = DbTaxonHist.rank_order
    elif taxon.startswith('f__'):
        col = DbTaxonHist.rank_family
    elif taxon.startswith('g__'):
        col = DbTaxonHist.rank_genus
    elif taxon.startswith('s__'):
        col = DbTaxonHist.rank_species
    else:
        col = None

    # If a prefix has been supplied, then we can just search that rank only
    if col:
        query = sm.select(col).where(col.ilike(f'{taxon}%')).distinct().limit(limit)
        results = db.exec(query).all()
        return TaxonSearchResponse(matches=list(results))

    # Run against all columns
    else:
        subqueries = list()
        for col in (
                DbTaxonHist.rank_domain,
                DbTaxonHist.rank_phylum,
                DbTaxonHist.rank_class,
                DbTaxonHist.rank_order,
                DbTaxonHist.rank_family,
                DbTaxonHist.rank_genus,
                DbTaxonHist.rank_species
        ):
            subquery = (sm.select(col).where(col.ilike(f'%{taxon}%')).distinct().limit(limit))
            subqueries.append(subquery)

        # Union the subqueries and run them
        query = union_all(*subqueries)
        results = db.exec(query).all()
        return TaxonSearchResponse(matches=[x[0] for x in results])


def results_from_previous_releases(
        search: str,
        db: Session,
        page: int | None = None,
        items_per_page: int | None = None
) -> TaxonPreviousReleasesPaginated:
    # Validate the input.
    search = search.strip()
    if len(search) == 0:
        raise HttpBadRequest('The taxon cannot be empty.')
    search = '%{}%'.format(search)

    # Create the subqueries for each rank
    subqueries = list()
    for rank in (
            DbTaxonHist.rank_domain,
            DbTaxonHist.rank_phylum,
            DbTaxonHist.rank_class,
            DbTaxonHist.rank_order,
            DbTaxonHist.rank_family,
            DbTaxonHist.rank_genus,
            DbTaxonHist.rank_species
    ):
        subqueries.append(sm.select(rank, DbTaxonHist.release_ver).where(rank.ilike(f'%{search}%')).distinct())

    # Execute the query
    results = db.exec(union_all(*subqueries)).all()
    rank_order_dict = {x: i for (i, x) in enumerate(GTDB_RELEASES)}

    # There's a case that exists where the case is slightly different for previous releases.
    # Therefore, if all the keys are the same (ignoring case), and the current release is present
    # then use the most recent releases capitalisation
    results = [(x.strip(), y.strip()) for (x, y) in results]

    d_oldest_taxon_name = dict()
    for cur_taxon, release_ver in results:
        cur_release = rank_order_dict[release_ver]
        if cur_release == rank_order_dict['NCBI']:
            continue
        if cur_taxon.lower() not in d_oldest_taxon_name:
            d_oldest_taxon_name[cur_taxon.lower()] = (cur_taxon, cur_release)
        elif cur_release > d_oldest_taxon_name[cur_taxon.lower()][1]:
            d_oldest_taxon_name[cur_taxon.lower()] = (cur_taxon, cur_release)

    all_hits = dict()
    for rank_name, release_ver in results:
        if rank_name.lower() in d_oldest_taxon_name:
            cur_rank_name = d_oldest_taxon_name[rank_name.lower()][0]
        else:
            cur_rank_name = rank_name

        # Store this release version for this rank.
        if cur_rank_name not in all_hits:
            all_hits[cur_rank_name] = set()
        all_hits[cur_rank_name].add(release_ver)

    out = dict()
    for rank_name, rank_set in all_hits.items():

        # Only interested in previous GTDB releases
        if CURRENT_RELEASE in rank_set:
            continue

        # Ignore those which only appear in NCBI
        if len(rank_set - {'NCBI', CURRENT_RELEASE}) == 0:
            continue

        if rank_name not in out:
            out[rank_name] = list()
        for cur_rank in sorted(rank_set, key=lambda x: rank_order_dict[x]):
            if cur_rank != 'NCBI':
                out[rank_name].append(cur_rank)

    out_list = list()
    for rank_name, rank_set in sorted(out.items()):
        sorted_taxa = sorted(rank_set, key=lambda x: rank_order_dict[x])
        out_list.append(TaxonPreviousReleases(taxon=rank_name,
                                              firstSeen=sorted_taxa[0],
                                              lastSeen=sorted_taxa[-1]))

    # Do pagination
    total_rows = len(out_list)
    if page and items_per_page:
        out_list = out_list[items_per_page * (page - 1): items_per_page * page]

    return TaxonPreviousReleasesPaginated(
        totalRows=total_rows,
        rows=out_list
    )


def get_gc_content_histogram_bins(taxon: str, db: Session) -> List[GraphHistogramBin]:
    # Select the target column to search
    if taxon.startswith('d__'):
        target_col = DbMetadataTaxonomy.gtdb_domain
    elif taxon.startswith('p__'):
        target_col = DbMetadataTaxonomy.gtdb_phylum
    elif taxon.startswith('c__'):
        target_col = DbMetadataTaxonomy.gtdb_class
    elif taxon.startswith('o__'):
        target_col = DbMetadataTaxonomy.gtdb_order
    elif taxon.startswith('f__'):
        target_col = DbMetadataTaxonomy.gtdb_family
    elif taxon.startswith('g__'):
        target_col = DbMetadataTaxonomy.gtdb_genus
    elif taxon.startswith('s__'):
        target_col = DbMetadataTaxonomy.gtdb_species
    else:
        raise HttpBadRequest(f'Invalid taxon {taxon}')

    # Select the GC values
    query = (
        sm.select(DbMetadataNucleotide.gc_percentage)
        .join(DbGenomes, DbMetadataNucleotide.id == DbGenomes.id)
        .join(DbMetadataTaxonomy, DbMetadataTaxonomy.id == DbGenomes.id)
        .where(target_col == taxon)
    )
    results = db.exec(query).all()

    if len(results) == 0:
        raise HttpBadRequest(f'Taxon {taxon} not found')

    # Compute the histogram bins
    counts, bin_edges = np.histogram(results, bins='auto')

    out = list()
    for i, count in enumerate(counts):
        out.append(GraphHistogramBin(x0=bin_edges[i], x1=bin_edges[i + 1], height=count))
    return out


def get_taxon_card(taxon: str, db_gtdb: Session) -> TaxonCard:
    idx_to_tax_col = (
        DbMetadataTaxonomy.gtdb_domain,
        DbMetadataTaxonomy.gtdb_phylum,
        DbMetadataTaxonomy.gtdb_class,
        DbMetadataTaxonomy.gtdb_order,
        DbMetadataTaxonomy.gtdb_family,
        DbMetadataTaxonomy.gtdb_genus,
        DbMetadataTaxonomy.gtdb_species,
    )
    idx_to_rank = ('Domain', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species')

    # Select the target column to search
    if taxon.startswith('d__'):
        rank_idx = 0
    elif taxon.startswith('p__'):
        rank_idx = 1
    elif taxon.startswith('c__'):
        rank_idx = 2
    elif taxon.startswith('o__'):
        rank_idx = 3
    elif taxon.startswith('f__'):
        rank_idx = 4
    elif taxon.startswith('g__'):
        rank_idx = 5
    elif taxon.startswith('s__'):
        rank_idx = 6
    else:
        raise HttpBadRequest(f'Invalid taxon {taxon}')

    target_col = idx_to_tax_col[rank_idx]
    cur_rank = idx_to_rank[rank_idx]
    higher_ranks = idx_to_tax_col[:rank_idx]

    # Make sure this taxon exists
    query_n_gids = sm.select(func.count('*')).where(target_col == taxon)
    n_genomes = db_gtdb.exec(query_n_gids).first()
    if n_genomes == 0:
        raise HttpBadRequest(f'Taxon {taxon} not found')

    # Find the higher ranks for this taxon
    if len(higher_ranks) > 0:

        query_higher_ranks = sm.select(*higher_ranks).where(target_col == taxon).distinct()
        results_higher_ranks = db_gtdb.exec(query_higher_ranks).all()

        if len(results_higher_ranks) != 1:
            raise HttpBadRequest(f'Taxon {taxon} not found')

        # Take each of the higher ranks and output it into a list
        if len(higher_ranks) > 1:
            higher_ranks_out = list(results_higher_ranks[0])
        else:
            higher_ranks_out = [results_higher_ranks[0]]
    else:
        higher_ranks_out = list()

    # Find the releases this taxon is present in
    return TaxonCard(
        nGenomes=n_genomes,
        rank=cur_rank,
        inReleases=[],
        higherRanks=higher_ranks_out
    )


def get_taxon_genomes_detail(taxon: str, sp_reps_only: bool, db: Session) -> TaxonGenomesDetailResponse:
    idx_to_tax_col = (
        DbMetadataTaxonomy.gtdb_domain,
        DbMetadataTaxonomy.gtdb_phylum,
        DbMetadataTaxonomy.gtdb_class,
        DbMetadataTaxonomy.gtdb_order,
        DbMetadataTaxonomy.gtdb_family,
        DbMetadataTaxonomy.gtdb_genus,
        DbMetadataTaxonomy.gtdb_species,
    )

    # Select the target column to search
    if taxon.startswith('d__'):
        rank_idx = 0
    elif taxon.startswith('p__'):
        rank_idx = 1
    elif taxon.startswith('c__'):
        rank_idx = 2
    elif taxon.startswith('o__'):
        rank_idx = 3
    elif taxon.startswith('f__'):
        rank_idx = 4
    elif taxon.startswith('g__'):
        rank_idx = 5
    elif taxon.startswith('s__'):
        rank_idx = 6
    else:
        raise HttpBadRequest(f'Invalid taxon {taxon}')
    target_col = idx_to_tax_col[rank_idx]

    query_n_gids = (
        sm.select(
            DbGenomes.name,
            DbMetadataTaxonomy.gtdb_domain,
            DbMetadataTaxonomy.gtdb_phylum,
            DbMetadataTaxonomy.gtdb_class,
            DbMetadataTaxonomy.gtdb_order,
            DbMetadataTaxonomy.gtdb_family,
            DbMetadataTaxonomy.gtdb_genus,
            DbMetadataTaxonomy.gtdb_species,
            DbMetadataTaxonomy.gtdb_representative
        )
        .join(DbMetadataTaxonomy, DbMetadataTaxonomy.id == DbGenomes.id)
        .join(DbMetadataNcbi, DbMetadataNcbi.id == DbGenomes.id)
        .where(target_col == taxon)
        .where(DbMetadataNcbi.ncbi_genbank_assembly_accession != None)
        .where(DbMetadataTaxonomy.gtdb_domain != 'd__')
        .where(DbMetadataTaxonomy.gtdb_phylum != 'p__')
        .where(DbMetadataTaxonomy.gtdb_class != 'c__')
        .where(DbMetadataTaxonomy.gtdb_order != 'o__')
        .where(DbMetadataTaxonomy.gtdb_family != 'f__')
        .where(DbMetadataTaxonomy.gtdb_genus != 'g__')
        .where(DbMetadataTaxonomy.gtdb_species != 's__')
        .order_by(DbMetadataTaxonomy.gtdb_domain)
        .order_by(DbMetadataTaxonomy.gtdb_phylum)
        .order_by(DbMetadataTaxonomy.gtdb_class)
        .order_by(DbMetadataTaxonomy.gtdb_order)
        .order_by(DbMetadataTaxonomy.gtdb_family)
        .order_by(DbMetadataTaxonomy.gtdb_genus)
        .order_by(DbMetadataTaxonomy.gtdb_species)
        .order_by(DbMetadataTaxonomy.gtdb_representative.desc())
        .order_by(DbGenomes.name)
    )
    if sp_reps_only:
        query_n_gids = query_n_gids.where(DbMetadataTaxonomy.gtdb_representative == True)

    db_rows = db.exec(query_n_gids).all()
    if len(db_rows) == 0:
        raise HttpNotFound(f'Taxon {taxon} not found')

    rows_out = list()
    for row in db_rows:
        rows_out.append(TaxonGenomesDetailRow(
            gid=row.name,
            gtdbIsRep=row.gtdb_representative,
            gtdbDomain=row.gtdb_domain,
            gtdbPhylum=row.gtdb_phylum,
            gtdbClass=row.gtdb_class,
            gtdbOrder=row.gtdb_order,
            gtdbFamily=row.gtdb_family,
            gtdbGenus=row.gtdb_genus,
            gtdbSpecies=row.gtdb_species
        ))
    return TaxonGenomesDetailResponse(rows=rows_out)
