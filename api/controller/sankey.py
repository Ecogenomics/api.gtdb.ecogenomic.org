import sqlmodel as sm
from sqlmodel import Session
from vtracker import VTracker

from api.config import GTDB_RELEASES
from api.db.gtdb_web import DbTaxonHist, DbTaxonHistoryMtView
from api.exceptions import HttpBadRequest
from api.model.sankey import SankeySearchRequest, SankeySearchResponse


def get_search_sankey(request: SankeySearchRequest, db: Session) -> SankeySearchResponse:
    """Returns the direct descendants below this taxon."""
    search = request.taxon
    release_from = request.releaseFrom
    release_to = request.releaseTo
    filter_rank = request.filterRank

    # Validate the input
    if search is None or len(search) <= 3:
        raise HttpBadRequest('Unsupported query, the rank must be > 3 characters.')

    # Create mappings between the release names and their indices.
    dict_releases = {x: i for (i, x) in enumerate(GTDB_RELEASES)}
    list_releases = GTDB_RELEASES
    long_releases = list()
    long_to_short = dict()

    for r in GTDB_RELEASES:
        if r.startswith('R'):
            long_name = f'Release {r[1:]}'
        else:
            long_name = r
        long_releases.append(long_name)
        long_to_short[long_name] = r

    # Verify the parameters
    if release_from is None or release_from not in dict_releases:
        raise HttpBadRequest('You must select a release to search from.')
    if release_to is None or release_to not in dict_releases:
        raise HttpBadRequest('You must select a release to search to.')
    if release_from == release_to:
        raise HttpBadRequest('You cannot compare the same release.')

    rank_cols = {'d__': 'rank_domain', 'p__': 'rank_phylum', 'c__': 'rank_class',
                 'o__': 'rank_order', 'f__': 'rank_family', 'g__': 'rank_genus',
                 's__': 'rank_species'}
    rank_cols_obj = {
        'd__': DbTaxonHist.rank_domain, 'p__': DbTaxonHist.rank_phylum, 'c__': DbTaxonHist.rank_class,
        'o__': DbTaxonHist.rank_order, 'f__': DbTaxonHist.rank_family, 'g__': DbTaxonHist.rank_genus,
        's__': DbTaxonHist.rank_species
    }
    rank_order = {'rank_domain': 0, 'rank_phylum': 1, 'rank_class': 2, 'rank_order': 3,
                  'rank_family': 4, 'rank_genus': 5, 'rank_species': 6}

    rank = search[0:3]
    rank_col = rank_cols.get(rank)
    rank_col_obj = rank_cols_obj.get(rank)

    # Double check that this rank actually exists.
    if rank_col is None:
        raise HttpBadRequest('You must specify a rank, e.g.: "d__Bacteria", instead of "Bacteria".')

    # Generate the list of columns to be used (i.e. the search must match in one of these ranks)
    sql_ranks = list_releases[dict_releases[release_from]:dict_releases[release_to] + 1]
    sql_ranks_obj = [getattr(DbTaxonHistoryMtView, x.replace('.', '_')) for x in sql_ranks]

    # Check if filter
    col_filter = rank_cols.get(filter_rank)
    col_filter = col_filter if col_filter else rank_col

    filter_rank_idx = rank_order.get(col_filter)
    search_rank_idx = rank_order.get(rank_col)

    # Find the higher ranks for this query.
    within = set()
    if filter_rank_idx < search_rank_idx:
        query = sm.select(rank_cols_obj[filter_rank]).where(rank_col_obj == search).distinct()
        results = db.exec(query).all()
        within = set(results)

    # Get rows for all genomes that have a taxonomic rank in any release matching the search term
    query = (
        sm.select(DbTaxonHistoryMtView.genome_id, *sql_ranks_obj)
        .where(DbTaxonHistoryMtView.genome_id.in_(
            sm.select(DbTaxonHist.genome_id)
            .where(rank_col_obj == search)
            .where(DbTaxonHist.release_ver.in_(sql_ranks))
        ))
    )
    results = db.exec(query).all()

    # Create the JSON for the sankey diagram
    selected_releases = long_releases[dict_releases[release_from]:dict_releases[release_to] + 1]
    vt = VTracker(selected_releases)
    for result in results:
        ver_info = dict()
        for cur_release in selected_releases:
            short_release = long_to_short[cur_release]

            # Unfortunately R86.2 has a decimal place, it must be replaced with an underscore for attribute access.
            if '.' in short_release:
                cur_ver_info = getattr(result, short_release.replace('.', '_'))
            else:
                cur_ver_info = getattr(result, short_release)

            if cur_ver_info is not None:
                cur_ranks = cur_ver_info.split(';')

                if filter_rank_idx < search_rank_idx:
                    if cur_ranks[filter_rank_idx] not in within:
                        cur_ver_info = '[%s]' % cur_ranks[filter_rank_idx]
                    else:
                        cur_ver_info = cur_ranks[filter_rank_idx]
                elif filter_rank_idx > search_rank_idx:
                    if cur_ranks[search_rank_idx] != search:
                        cur_ver_info = '[%s]' % cur_ranks[filter_rank_idx]
                    else:
                        cur_ver_info = cur_ranks[filter_rank_idx]
                else:
                    cur_ver_info = cur_ranks[search_rank_idx]

                ver_info[cur_release] = '%s: %s' % (short_release, cur_ver_info)
            else:
                ver_info[cur_release] = '%s: Not Present' % short_release
        vt.add(result.genome_id, ver_info)

    the_json = vt.as_sankey_json()
    return SankeySearchResponse(**the_json)
