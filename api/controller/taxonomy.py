from typing import List, Dict

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from api.config import GTDB_RELEASES
from api.db.models import GtdbSpeciesClusterCount, GtdbWebTaxaNotInLit, GtdbWebTaxonHist
from api.exceptions import HttpBadRequest, HttpNotFound
from api.model.taxonomy import TaxonomyCount, TaxonomyCountRequest, TaxonomyCountResponse, \
    TaxaNotInLiterature, TaxonomyOptional, TaxonomyOptionalRelease


def add_gtdb_proposed_taxa_to_query(query, gtdb_web: Session) -> Select:
    """Take the lowest rank taxon and append that to the query."""
    d, p, c, o, f, g, s = [set() for _ in range(7)]
    for taxon in taxa_not_in_lit(gtdb_web):
        for cur_set, rank in ((s, taxon.taxonomy.s), (g, taxon.taxonomy.g), (f, taxon.taxonomy.f),
                              (o, taxon.taxonomy.o), (c, taxon.taxonomy.c), (p, taxon.taxonomy.p),
                              (d, taxon.taxonomy.d)):
            if rank is not None:
                cur_set.add(rank)
                break

    conditions = list()
    for col, taxa in ((GtdbSpeciesClusterCount.gtdb_domain, d), (GtdbSpeciesClusterCount.gtdb_phylum, p),
                      (GtdbSpeciesClusterCount.gtdb_class, c), (GtdbSpeciesClusterCount.gtdb_order, o),
                      (GtdbSpeciesClusterCount.gtdb_family, f), (GtdbSpeciesClusterCount.gtdb_genus, g),
                      (GtdbSpeciesClusterCount.gtdb_species, s)):
        if len(taxa) > 0:
            conditions.append(col.in_(taxa))

    out = query
    if len(conditions) > 0:
        out = out.where(sa.or_(*conditions))
    return out


def post_taxonomy_count(request: TaxonomyCountRequest, db_gtdb: Session, gtdb_web: Session) -> TaxonomyCountResponse:
    """Returns the number of genomes in each species cluster."""

    query = sa.select([GtdbSpeciesClusterCount.gtdb_domain,
                       GtdbSpeciesClusterCount.gtdb_phylum,
                       GtdbSpeciesClusterCount.gtdb_class,
                       GtdbSpeciesClusterCount.gtdb_order,
                       GtdbSpeciesClusterCount.gtdb_family,
                       GtdbSpeciesClusterCount.gtdb_genus,
                       GtdbSpeciesClusterCount.gtdb_species,
                       GtdbSpeciesClusterCount.cnt])

    # If the user is requesting only GTDB proposed names, create a filter for these
    if request.proposed:
        query = add_gtdb_proposed_taxa_to_query(query, gtdb_web)

    # Determine the order_by clause
    if request.sortBy and request.sortDesc and 0 < len(request.sortBy) == len(request.sortDesc):
        order_by = list()
        for sort_by, sort_desc in zip(request.sortBy, request.sortDesc):
            if sort_by == 'd':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_domain.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_domain.asc())
            elif sort_by == 'p':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_phylum.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_phylum)
            elif sort_by == 'c':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_class.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_class)
            elif sort_by == 'o':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_order.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_order)
            elif sort_by == 'f':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_family.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_family)
            elif sort_by == 'g':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_genus.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_genus)
            elif sort_by == 's':
                order_by.append(
                    GtdbSpeciesClusterCount.gtdb_species.desc() if sort_desc else GtdbSpeciesClusterCount.gtdb_species)
            elif sort_by == 'count':
                order_by.append(GtdbSpeciesClusterCount.cnt.desc() if sort_desc else GtdbSpeciesClusterCount.cnt)
            else:
                raise HttpBadRequest(f'Unknown sortBy: {sort_by}')
        query = query.order_by(*order_by)

    # Add search
    if request.search:
        query = query.where(
            sa.or_(
                GtdbSpeciesClusterCount.gtdb_domain.ilike(f'%{request.search}%'),
                GtdbSpeciesClusterCount.gtdb_phylum.ilike(f'%{request.search}%'),
                GtdbSpeciesClusterCount.gtdb_class.ilike(f'%{request.search}%'),
                GtdbSpeciesClusterCount.gtdb_order.ilike(f'%{request.search}%'),
                GtdbSpeciesClusterCount.gtdb_family.ilike(f'%{request.search}%'),
                GtdbSpeciesClusterCount.gtdb_genus.ilike(f'%{request.search}%'),
                GtdbSpeciesClusterCount.gtdb_species.ilike(f'%{request.search}%')
            )
        )

    # Add column-specific filtering if present
    if request.filterDomain:
        query = query.where(GtdbSpeciesClusterCount.gtdb_domain.ilike(f'%{request.filterDomain}%'))
    if request.filterPhylum:
        query = query.where(GtdbSpeciesClusterCount.gtdb_phylum.ilike(f'%{request.filterPhylum}%'))
    if request.filterClass:
        query = query.where(GtdbSpeciesClusterCount.gtdb_class.ilike(f'%{request.filterClass}%'))
    if request.filterOrder:
        query = query.where(GtdbSpeciesClusterCount.gtdb_order.ilike(f'%{request.filterOrder}%'))
    if request.filterFamily:
        query = query.where(GtdbSpeciesClusterCount.gtdb_family.ilike(f'%{request.filterFamily}%'))
    if request.filterGenus:
        query = query.where(GtdbSpeciesClusterCount.gtdb_genus.ilike(f'%{request.filterGenus}%'))
    if request.filterSpecies:
        query = query.where(GtdbSpeciesClusterCount.gtdb_species.ilike(f'%{request.filterSpecies}%'))

    # Get the total number of rows in the table before pagination
    total_rows = db_gtdb.execute(sa.select(sa.func.count()).select_from(query)).scalar()

    # Add pagination
    if request.itemsPerPage and request.page:
        query = query.limit(request.itemsPerPage)
        query = query.offset(request.itemsPerPage * (request.page - 1))

    # Run the query and return the results
    rows = list()
    for row in db_gtdb.execute(query):
        rows.append(TaxonomyCount(d=row.gtdb_domain,
                                  p=row.gtdb_phylum,
                                  c=row.gtdb_class,
                                  o=row.gtdb_order,
                                  f=row.gtdb_family,
                                  g=row.gtdb_genus,
                                  s=row.gtdb_species,
                                  count=row.cnt))
    return TaxonomyCountResponse(totalRows=total_rows, rows=rows)


def taxonomy_count_rows_to_sv(data: TaxonomyCountResponse) -> List[List[str]]:
    out = list()

    # Exit early if no data
    rows = data.rows
    if len(rows) == 0:
        return out

    out.append(['Domain', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species', 'No. genomes'])
    for row in rows:
        out.append([row.d, row.p, row.c, row.o, row.f, row.g, row.s, row.count])
    return out


def taxonomy_partial_search_all_releases(taxon: str, db: Session) -> List[TaxonomyOptionalRelease]:
    cols = (GtdbWebTaxonHist.rank_domain, GtdbWebTaxonHist.rank_phylum,
            GtdbWebTaxonHist.rank_class, GtdbWebTaxonHist.rank_order,
            GtdbWebTaxonHist.rank_family, GtdbWebTaxonHist.rank_genus,
            GtdbWebTaxonHist.rank_species)

    select_cols = list()
    if taxon.startswith('d__'):
        select_cols.extend(cols[0:1])
        where_col = cols[0]
        taxon_col_idx = 0
    elif taxon.startswith('p__'):
        select_cols.extend(cols[0:2])
        where_col = cols[1]
        taxon_col_idx = 1
    elif taxon.startswith('c__'):
        select_cols.extend(cols[0:3])
        where_col = cols[2]
        taxon_col_idx = 2
    elif taxon.startswith('o__'):
        select_cols.extend(cols[0:4])
        where_col = cols[3]
        taxon_col_idx = 3
    elif taxon.startswith('f__'):
        select_cols.extend(cols[0:5])
        where_col = cols[4]
        taxon_col_idx = 4
    elif taxon.startswith('g__'):
        select_cols.extend(cols[0:6])
        where_col = cols[5]
        taxon_col_idx = 5
    elif taxon.startswith('s__'):
        select_cols.extend(cols[0:7])
        where_col = cols[6]
        taxon_col_idx = 6
    else:
        raise HttpBadRequest('You must specify using a greengenes format.')

    select_cols.append(GtdbWebTaxonHist.release_ver)
    query = sa.select(select_cols).where(where_col.ilike(f'{taxon}%')).distinct()

    results = list(db.execute(query))
    if len(results) == 0:
        raise HttpNotFound(f'{taxon} not found.')

    # Iterate over the rows to extract the release versions
    d_release_to_data: Dict[str, TaxonomyOptional] = dict()
    out = list()
    for result in results:
        # Polyphyletic groups will match, e.g. taxon='Abc' could match 'Abc_A'
        if result[taxon_col_idx] != taxon:
            continue

        # Extract the taxa at each rank
        d_result = dict(result)
        out.append(TaxonomyOptionalRelease(release=d_result['release_ver'].strip(),
                                           taxonomy=TaxonomyOptional(
                                               d=d_result.get('rank_domain'),
                                               p=d_result.get('rank_phylum'),
                                               c=d_result.get('rank_class'),
                                               o=d_result.get('rank_order'),
                                               f=d_result.get('rank_family'),
                                               g=d_result.get('rank_genus'),
                                               s=d_result.get('rank_species')
                                           )))

    return sorted(out, key=lambda x: GTDB_RELEASES.index(x.release), reverse=True)


def taxonomy_partial_search(taxon: str, db: Session) -> TaxonomyOptional:
    cols = [GtdbSpeciesClusterCount.gtdb_domain, GtdbSpeciesClusterCount.gtdb_phylum,
            GtdbSpeciesClusterCount.gtdb_class, GtdbSpeciesClusterCount.gtdb_order,
            GtdbSpeciesClusterCount.gtdb_family, GtdbSpeciesClusterCount.gtdb_genus,
            GtdbSpeciesClusterCount.gtdb_species]

    if taxon.startswith('d__'):
        select_cols = cols[0:1]
        where_col = cols[0]
        taxon_idx = 0
    elif taxon.startswith('p__'):
        select_cols = cols[0:2]
        where_col = cols[1]
        taxon_idx = 1
    elif taxon.startswith('c__'):
        select_cols = cols[0:3]
        where_col = cols[2]
        taxon_idx = 2
    elif taxon.startswith('o__'):
        select_cols = cols[0:4]
        where_col = cols[3]
        taxon_idx = 3
    elif taxon.startswith('f__'):
        select_cols = cols[0:5]
        where_col = cols[4]
        taxon_idx = 4
    elif taxon.startswith('g__'):
        select_cols = cols[0:6]
        where_col = cols[5]
        taxon_idx = 5
    elif taxon.startswith('s__'):
        select_cols = cols[0:7]
        where_col = cols[6]
        taxon_idx = 6
    else:
        raise HttpBadRequest('You must specify using a greengenes format.')

    query = sa.select(select_cols).where(where_col.ilike(f'{taxon[3:]}%')).distinct()

    results = list(db.execute(query))
    if len(results) == 0:
        raise HttpNotFound(f'{taxon} not found.')

    result_row = results[0]

    # this can happen if its a polyphyletic group, take the exact match
    if len(results) > 1:
        exact_match = [x for x in results if x[taxon_idx] == taxon[3:]]
        if len(exact_match) == 0:
            raise HttpNotFound(f'{taxon} not found.')
        result_row = exact_match[0]

    out = dict()
    if taxon.startswith('d__'):
        out['d'] = f'd__{result_row[0]}'
    elif taxon.startswith('p__'):
        out['p'] = f'p__{result_row[1]}'
    elif taxon.startswith('c__'):
        out['c'] = f'c__{result_row[2]}'
    elif taxon.startswith('o__'):
        out['o'] = f'o__{result_row[3]}'
    elif taxon.startswith('f__'):
        out['f'] = f'f__{result_row[4]}'
    elif taxon.startswith('g__'):
        out['g'] = f'g__{result_row[5]}'
    elif taxon.startswith('s__'):
        out['s'] = f's__{result_row[6]}'

    d_results = dict(result_row)
    return TaxonomyOptional(
        d=d_results.get('gtdb_domain'),
        p=d_results.get('gtdb_phylum'),
        c=d_results.get('gtdb_class'),
        o=d_results.get('gtdb_order'),
        f=d_results.get('gtdb_family'),
        g=d_results.get('gtdb_genus'),
        s=d_results.get('gtdb_species')
    )


def taxa_not_in_lit(db: Session) -> List[TaxaNotInLiterature]:
    rows = db.query(GtdbWebTaxaNotInLit).all()
    out = list()
    for row in rows:
        out.append(TaxaNotInLiterature(taxon=row.taxon,
                                       taxonomy=TaxonomyOptional(d=row.gtdb_domain,
                                                                 p=row.gtdb_phylum,
                                                                 c=row.gtdb_class,
                                                                 o=row.gtdb_order,
                                                                 f=row.gtdb_family,
                                                                 g=row.gtdb_genus,
                                                                 s=row.gtdb_species),
                                       appearedInRelease=row.appeared_in_release,
                                       taxonStatus=row.taxon_status,
                                       notes=row.notes))
    return out
