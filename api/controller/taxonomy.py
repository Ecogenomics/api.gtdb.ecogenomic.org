from typing import List

import sqlmodel as sm
from sqlmodel import Session

from api.config import GTDB_RELEASES
from api.db.gtdb import DbGtdbSpeciesClusterCount
from api.db.gtdb_web import DbGtdbTaxaNotInLit, DbTaxonHist
from api.exceptions import HttpBadRequest, HttpNotFound
from api.model.taxonomy import TaxonomyCount, TaxonomyCountRequest, TaxonomyCountResponse, \
    TaxaNotInLiterature, TaxonomyOptional, TaxonomyOptionalRelease


def add_gtdb_proposed_taxa_to_query(query, gtdb_web: Session):
    """Take the lowest rank taxon and append that to the query."""
    d, p, c, o, f, g, s = [set() for _ in range(7)]
    for taxon in taxa_not_in_lit(gtdb_web):
        for cur_set, rank in (
                (s, taxon.taxonomy.s), (g, taxon.taxonomy.g), (f, taxon.taxonomy.f),
                (o, taxon.taxonomy.o), (c, taxon.taxonomy.c), (p, taxon.taxonomy.p),
                (d, taxon.taxonomy.d)
        ):
            if rank is not None:
                cur_set.add(rank)
                break

    conditions = list()
    for col, taxa in (
            (DbGtdbSpeciesClusterCount.gtdb_domain, d), (DbGtdbSpeciesClusterCount.gtdb_phylum, p),
            (DbGtdbSpeciesClusterCount.gtdb_class, c), (DbGtdbSpeciesClusterCount.gtdb_order, o),
            (DbGtdbSpeciesClusterCount.gtdb_family, f), (DbGtdbSpeciesClusterCount.gtdb_genus, g),
            (DbGtdbSpeciesClusterCount.gtdb_species, s)
    ):
        if len(taxa) > 0:
            conditions.append(col.in_(taxa))

    out = query
    if len(conditions) > 0:
        out = out.where(sm.or_(*conditions))
    return out


def post_taxonomy_count(request: TaxonomyCountRequest, db_gtdb: Session, gtdb_web: Session) -> TaxonomyCountResponse:
    """Returns the number of genomes in each species cluster."""
    query = sm.select(
        DbGtdbSpeciesClusterCount.gtdb_domain,
        DbGtdbSpeciesClusterCount.gtdb_phylum,
        DbGtdbSpeciesClusterCount.gtdb_class,
        DbGtdbSpeciesClusterCount.gtdb_order,
        DbGtdbSpeciesClusterCount.gtdb_family,
        DbGtdbSpeciesClusterCount.gtdb_genus,
        DbGtdbSpeciesClusterCount.gtdb_species,
        DbGtdbSpeciesClusterCount.cnt
    )

    # If the user is requesting only GTDB proposed names, create a filter for these
    if request.proposed:
        query = add_gtdb_proposed_taxa_to_query(query, gtdb_web)

    # Determine the order_by clause
    if request.sortBy and request.sortDesc and 0 < len(request.sortBy) == len(request.sortDesc):
        order_by = list()
        for sort_by, sort_desc in zip(request.sortBy, request.sortDesc):
            if sort_by == 'd':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_domain.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_domain.asc())
            elif sort_by == 'p':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_phylum.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_phylum)
            elif sort_by == 'c':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_class.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_class)
            elif sort_by == 'o':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_order.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_order)
            elif sort_by == 'f':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_family.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_family)
            elif sort_by == 'g':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_genus.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_genus)
            elif sort_by == 's':
                order_by.append(
                    DbGtdbSpeciesClusterCount.gtdb_species.desc() if sort_desc else DbGtdbSpeciesClusterCount.gtdb_species)
            elif sort_by == 'count':
                order_by.append(DbGtdbSpeciesClusterCount.cnt.desc() if sort_desc else DbGtdbSpeciesClusterCount.cnt)
            else:
                raise HttpBadRequest(f'Unknown sortBy: {sort_by}')
        query = query.order_by(*order_by)

    # Add search
    if request.search:
        query = query.where(
            sm.or_(
                DbGtdbSpeciesClusterCount.gtdb_domain.ilike(f'%{request.search}%'),
                DbGtdbSpeciesClusterCount.gtdb_phylum.ilike(f'%{request.search}%'),
                DbGtdbSpeciesClusterCount.gtdb_class.ilike(f'%{request.search}%'),
                DbGtdbSpeciesClusterCount.gtdb_order.ilike(f'%{request.search}%'),
                DbGtdbSpeciesClusterCount.gtdb_family.ilike(f'%{request.search}%'),
                DbGtdbSpeciesClusterCount.gtdb_genus.ilike(f'%{request.search}%'),
                DbGtdbSpeciesClusterCount.gtdb_species.ilike(f'%{request.search}%')
            )
        )

    # Add column-specific filtering if present
    if request.filterDomain:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_domain.ilike(f'%{request.filterDomain}%'))
    if request.filterPhylum:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_phylum.ilike(f'%{request.filterPhylum}%'))
    if request.filterClass:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_class.ilike(f'%{request.filterClass}%'))
    if request.filterOrder:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_order.ilike(f'%{request.filterOrder}%'))
    if request.filterFamily:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_family.ilike(f'%{request.filterFamily}%'))
    if request.filterGenus:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_genus.ilike(f'%{request.filterGenus}%'))
    if request.filterSpecies:
        query = query.where(DbGtdbSpeciesClusterCount.gtdb_species.ilike(f'%{request.filterSpecies}%'))

    # Get the total number of rows in the table before pagination
    total_rows = db_gtdb.exec(sm.select(sm.func.count()).select_from(query)).first()

    # Add pagination
    if request.itemsPerPage and request.page:
        query = query.limit(request.itemsPerPage)
        query = query.offset(request.itemsPerPage * (request.page - 1))

    # Run the query and return the results
    rows = list()
    for row in db_gtdb.exec(query):
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
    cols = (DbTaxonHist.rank_domain, DbTaxonHist.rank_phylum,
            DbTaxonHist.rank_class, DbTaxonHist.rank_order,
            DbTaxonHist.rank_family, DbTaxonHist.rank_genus,
            DbTaxonHist.rank_species)

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

    select_cols.append(DbTaxonHist.release_ver)
    query = sm.select(*select_cols, ).where(where_col.ilike(f'{taxon}%')).distinct()

    results = list(db.exec(query).all())
    if len(results) == 0:
        raise HttpNotFound(f'{taxon} not found.')

    # Iterate over the rows to extract the release versions
    out = list()
    for result in results:
        # Polyphyletic groups will match, e.g. taxon='Abc' could match 'Abc_A'
        if result[taxon_col_idx] != taxon:
            continue

        # Extract the taxa at each rank
        out.append(
            TaxonomyOptionalRelease(
                release=result.release_ver.strip(),
                taxonomy=TaxonomyOptional(
                    d=getattr(result, 'rank_domain', None),
                    p=getattr(result, 'rank_phylum', None),
                    c=getattr(result, 'rank_class', None),
                    o=getattr(result, 'rank_order', None),
                    f=getattr(result, 'rank_family', None),
                    g=getattr(result, 'rank_genus', None),
                    s=getattr(result, 'rank_species', None)
                )
            )
        )

    return sorted(out, key=lambda x: GTDB_RELEASES.index(x.release), reverse=True)


def taxonomy_partial_search(taxon: str, db: Session) -> TaxonomyOptional:
    cols = [
        DbGtdbSpeciesClusterCount.gtdb_domain, DbGtdbSpeciesClusterCount.gtdb_phylum,
        DbGtdbSpeciesClusterCount.gtdb_class, DbGtdbSpeciesClusterCount.gtdb_order,
        DbGtdbSpeciesClusterCount.gtdb_family, DbGtdbSpeciesClusterCount.gtdb_genus,
        DbGtdbSpeciesClusterCount.gtdb_species
    ]

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

    query = sm.select(*select_cols, ).where(where_col.ilike(f'{taxon[3:]}%')).distinct()

    results = list(db.exec(query).all())
    if len(results) == 0:
        raise HttpNotFound(f'{taxon} not found.')

    result_row = results[0]

    # this can happen if its a polyphyletic group, take the exact match
    if len(results) > 1:
        exact_match = [x for x in results if x[taxon_idx] == taxon[3:]]
        if len(exact_match) == 0:
            raise HttpNotFound(f'{taxon} not found.')
        result_row = exact_match[0]

    return TaxonomyOptional(
        d=getattr(result_row, 'gtdb_domain', None),
        p=getattr(result_row, 'gtdb_phylum', None),
        c=getattr(result_row, 'gtdb_class', None),
        o=getattr(result_row, 'gtdb_order', None),
        f=getattr(result_row, 'gtdb_family', None),
        g=getattr(result_row, 'gtdb_genus', None),
        s=getattr(result_row, 'gtdb_species', None)
    )


def taxa_not_in_lit(db: Session) -> List[TaxaNotInLiterature]:
    query = sm.select(DbGtdbTaxaNotInLit)
    rows = db.exec(query).all()
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
