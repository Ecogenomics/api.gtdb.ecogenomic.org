from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.orm import Session

from api.db.models import GtdbSpeciesClusterCount, DbGtdbTree, DbGtdbTreeChildren, GtdbWebTaxonHist, MetadataTaxonomy, \
    Genome
from api.exceptions import HttpBadRequest
from api.model.taxon import TaxonDescendants, TaxonSearchResponse, TaxonPreviousReleases


def get_taxon_descendants(taxon: str, db: Session) -> List[TaxonDescendants]:
    """Returns the direct descendants below this taxon."""

    # TODO: Convert this into once nested query.

    # Get parent info
    taxon_query = sa.select([DbGtdbTree.id]).where(DbGtdbTree.taxon == taxon)
    taxon_results = db.execute(taxon_query).fetchall()

    if len(taxon_results) != 1:
        raise HttpBadRequest(f'Taxon {taxon} not found')
    parent_id = taxon_results[0].id

    # Get the child info
    children_query = sa.select([DbGtdbTree.taxon, DbGtdbTree.total,
                                DbGtdbTree.type, DbGtdbTree.is_rep,
                                DbGtdbTree.type_material]) \
        .filter(DbGtdbTreeChildren.child_id == DbGtdbTree.id) \
        .where(DbGtdbTreeChildren.parent_id == parent_id) \
        .order_by(DbGtdbTreeChildren.order_id)

    for result in db.execute(children_query):
        yield TaxonDescendants(taxon=result.taxon,
                               total=result.total,
                               isGenome=result.type == 'genome',
                               isRep=result.is_rep,
                               typeMaterial=result.type_material)


def search_for_taxon(taxon: str, limit: Optional[int], db: Session) -> TaxonSearchResponse:
    # Maximum number of results to be returned
    if limit:
        limit = max(limit, 100)
    else:
        limit = 100

    if taxon.startswith('d__'):
        col = GtdbSpeciesClusterCount.gtdb_domain
        prefix = 'd__'
    elif taxon.startswith('p__'):
        col = GtdbSpeciesClusterCount.gtdb_phylum
        prefix = 'p__'
    elif taxon.startswith('c__'):
        col = GtdbSpeciesClusterCount.gtdb_class
        prefix = 'c__'
    elif taxon.startswith('o__'):
        col = GtdbSpeciesClusterCount.gtdb_order
        prefix = 'o__'
    elif taxon.startswith('f__'):
        col = GtdbSpeciesClusterCount.gtdb_family
        prefix = 'f__'
    elif taxon.startswith('g__'):
        col = GtdbSpeciesClusterCount.gtdb_genus
        prefix = 'g__'
    elif taxon.startswith('s__'):
        col = GtdbSpeciesClusterCount.gtdb_species
        prefix = 's__'
    else:
        prefix = taxon[0:3]
        col = None

    # Shortcut and only use one column
    if col:
        query = sa.select([col]).where(col.ilike(f'{taxon[3:]}%')).limit(limit).distinct()
        return TaxonSearchResponse(matches=[f'{prefix}{x[0]}' for x in db.execute(query)])

    # Run against all columns
    else:
        all_results = list()
        for col, prefix in [(GtdbSpeciesClusterCount.gtdb_domain, 'd__'),
                            (GtdbSpeciesClusterCount.gtdb_phylum, 'p__'),
                            (GtdbSpeciesClusterCount.gtdb_class, 'c__'),
                            (GtdbSpeciesClusterCount.gtdb_order, 'o__'),
                            (GtdbSpeciesClusterCount.gtdb_family, 'f__'),
                            (GtdbSpeciesClusterCount.gtdb_genus, 'g__'),
                            (GtdbSpeciesClusterCount.gtdb_species, 's__')]:
            query = sa.select([col]).where(col.ilike(f'%{taxon}%')).limit(limit).distinct()
            all_results.extend([f'{prefix}{x[0]}' for x in db.execute(query)])
        return TaxonSearchResponse(matches=all_results)


def get_taxon_genomes_in_taxon(taxon: str, sp_reps_only: bool, db: Session) -> List[str]:
    rank_to_col = {'d__': MetadataTaxonomy.gtdb_domain,
                   'p__': MetadataTaxonomy.gtdb_phylum,
                   'c__': MetadataTaxonomy.gtdb_class,
                   'o__': MetadataTaxonomy.gtdb_order,
                   'f__': MetadataTaxonomy.gtdb_family,
                   'g__': MetadataTaxonomy.gtdb_genus,
                   's__': MetadataTaxonomy.gtdb_species}
    col = rank_to_col.get(taxon[0:3])
    if not col:
        raise HttpBadRequest('Taxon must be in green-genes format, e.g. "g__Foo"')

    query = sa.select([Genome.name]). \
        select_from(sa.join(Genome, MetadataTaxonomy)). \
        where(col == taxon). \
        order_by(Genome.name)

    if sp_reps_only:
        query = query.where(MetadataTaxonomy.gtdb_representative == True)

    for row in db.execute(query):
        yield str(row.name)


def search_for_taxon_all_releases(taxon: str, limit: Optional[int], db: Session) -> TaxonSearchResponse:
    # Maximum number of results to be returned
    if limit:
        limit = max(limit, 100)
    else:
        limit = 100

    if taxon.startswith('d__'):
        col = GtdbWebTaxonHist.rank_domain
    elif taxon.startswith('p__'):
        col = GtdbWebTaxonHist.rank_phylum
    elif taxon.startswith('c__'):
        col = GtdbWebTaxonHist.rank_class
    elif taxon.startswith('o__'):
        col = GtdbWebTaxonHist.rank_order
    elif taxon.startswith('f__'):
        col = GtdbWebTaxonHist.rank_family
    elif taxon.startswith('g__'):
        col = GtdbWebTaxonHist.rank_genus
    elif taxon.startswith('s__'):
        col = GtdbWebTaxonHist.rank_species
    else:
        col = None

    # Shortcut and only use one column
    if col:
        query = sa.select([col]).where(col.ilike(f'{taxon}%')).limit(limit).distinct()
        return TaxonSearchResponse(matches=[str(x[0]) for x in db.execute(query)])

    # Run against all columns
    else:
        all_results = list()
        for col in (GtdbWebTaxonHist.rank_domain, GtdbWebTaxonHist.rank_phylum,
                    GtdbWebTaxonHist.rank_class, GtdbWebTaxonHist.rank_order,
                    GtdbWebTaxonHist.rank_family, GtdbWebTaxonHist.rank_genus,
                    GtdbWebTaxonHist.rank_species):
            query = sa.select([col]).where(col.ilike(f'%{taxon}%')).limit(limit).distinct()
            all_results.extend([str(x[0]) for x in db.execute(query)])
        return TaxonSearchResponse(matches=all_results)


def results_from_previous_releases(search: str, db: Session) -> List[TaxonPreviousReleases]:
    # Validate the input.
    search = search.strip()
    if len(search) <= 0:
        raise HttpBadRequest('The search query must be greater than 3 characters.')
    search = '%{}%'.format(search)

    # Additionally, search the taxon history database to check if this is a synonym.
    query = sql.text("""SELECT DISTINCT rank_domain AS rank_name, release_ver FROM taxon_hist WHERE rank_domain ILIKE :arg
                            UNION ALL
                        SELECT DISTINCT rank_phylum, release_ver FROM taxon_hist WHERE rank_phylum ILIKE :arg
                            UNION ALL
                        SELECT DISTINCT rank_class, release_ver FROM taxon_hist WHERE rank_class ILIKE :arg
                            UNION ALL
                        SELECT DISTINCT rank_order, release_ver FROM taxon_hist WHERE rank_order ILIKE :arg
                            UNION ALL
                        SELECT DISTINCT rank_family, release_ver FROM taxon_hist WHERE rank_family ILIKE :arg
                            UNION ALL
                        SELECT DISTINCT rank_genus, release_ver FROM taxon_hist WHERE rank_genus ILIKE :arg
                            UNION ALL
                        SELECT DISTINCT rank_species, release_ver FROM taxon_hist WHERE rank_species ILIKE :arg;""")
    results = db.execute(query, {'arg': search})

    rank_order_dict = {'R80': 0, 'R83': 1, 'R86.2': 2, 'R89': 3, 'R95': 4, 'R202': 5, 'R207': 6, 'NCBI': 7}

    # There's a case that exists where the case is slightly different for previous releases.
    # Therefore, if all the keys are the same (ignoring case), and the current release is present
    # then use the most recent releases capitalisation
    results = [(x.rank_name.strip(), x.release_ver.strip()) for x in results]
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
        if 'R207' in rank_set:
            continue

        # Ignore those which only appear in NCBI
        if len(rank_set - {'NCBI', 'R207'}) == 0:
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
    return out_list
