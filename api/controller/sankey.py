from sqlalchemy import sql
from sqlalchemy.orm import Session
from vtracker import VTracker

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

    dict_releases = {'R80': 0, 'R83': 1, 'R86.2': 2, 'R89': 3, 'R95': 4, 'R202': 5, 'R207': 6, 'NCBI': 7}
    list_releases = ['R80', 'R83', 'R86.2', 'R89', 'R95', 'R202', 'R207', 'NCBI']
    long_releases = ['Release 80', 'Release 83', 'Release 86.2', 'Release 89', 'Release 95',
                     'Release 202', 'Release 207', 'NCBI']
    long_to_short = {'Release 80': 'R80',
                     'Release 83': 'R83',
                     'Release 86.2': 'R86.2',
                     'Release 89': 'R89',
                     'Release 95': 'R95',
                     'Release 202': 'R202',
                     'Release 207': 'R207',
                     'NCBI': 'NCBI'}
    if release_from is None or release_from not in dict_releases:
        raise HttpBadRequest('You must select a release to search from.')
    if release_to is None or release_to not in dict_releases:
        raise HttpBadRequest('You must select a release to search to.')

    if release_from == release_to:
        raise HttpBadRequest('You cannot compare the same release.')

    rank_cols = {'d__': 'rank_domain', 'p__': 'rank_phylum', 'c__': 'rank_class',
                 'o__': 'rank_order', 'f__': 'rank_family', 'g__': 'rank_genus',
                 's__': 'rank_species'}
    rank_order = {'rank_domain': 0, 'rank_phylum': 1, 'rank_class': 2, 'rank_order': 3,
                  'rank_family': 4, 'rank_genus': 5, 'rank_species': 6}

    rank = search[0:3]
    rank_col = rank_cols.get(rank)

    # Double check that this rank actually exists.
    if rank_col is None:
        raise HttpBadRequest('You must specify a rank, e.g.: "p__Firmicutes", instead of "Firmicutes".')

    # Generate the list of columns to be used (i.e. the search must match in one of these ranks)
    sql_ranks = "'', ''".join(list_releases[dict_releases[release_from]:dict_releases[release_to] + 1])
    sql_ranks = "''" + sql_ranks + "''"

    # Check if filter
    col_filter = rank_cols.get(filter_rank)
    col_filter = col_filter if col_filter else rank_col

    filter_rank_idx = rank_order.get(col_filter)
    search_rank_idx = rank_order.get(rank_col)

    # Find the higher ranks for this query.
    within = set()
    if filter_rank_idx < search_rank_idx:
        query = sql.text("""SELECT DISTINCT {col} AS rank FROM taxon_hist WHERE {rank_col} = :rank;
                """.format(col=rank_cols.get(filter_rank), rank_col=rank_col))
        results = db.execute(query, {'rank': search})
        within = {x.rank for x in results}

    # Get a row containing the genome and which ranks it was in for each release.
    query = sql.text("""SELECT genome_id, "R80", "R83", "R86.2", "R89", "R95", "R202", "R207", "NCBI"
                              FROM CROSSTAB(
                                           'SELECT genome_id, release_ver, CONCAT(rank_domain, '';'', rank_phylum, '';'',
        rank_class, '';'', rank_order, '';'', rank_family, '';'', rank_genus, '';'', rank_species) AS taxonomy
                            FROM taxon_hist
                            WHERE genome_id IN (
                            SELECT DISTINCT genome_id FROM taxon_hist
                            WHERE release_ver IN ({sql_ranks})
                                  AND {col} = ':rank')
                            ORDER BY genome_id ASC, release_ver ASC;'
                                                       ,
                                   'SELECT DISTINCT release_ver FROM taxon_hist ORDER BY release_ver ASC')
                               AS ct (genome_id CHAR(10), "NCBI" VARCHAR, "R202" VARCHAR, "R207" VARCHAR, "R80" VARCHAR, "R83" VARCHAR, "R86.2" VARCHAR,
                                      "R89" VARCHAR, "R95" VARCHAR);""".format(col=rank_col, sql_ranks=sql_ranks))
    results = db.execute(query, {'rank': search})

    selected_releases = long_releases[dict_releases[release_from]:dict_releases[release_to] + 1]
    vt = VTracker(selected_releases)
    for result in results:
        ver_info = dict()
        for cur_release in selected_releases:
            short_release = long_to_short[cur_release]
            cur_ver_info = result[short_release]
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
