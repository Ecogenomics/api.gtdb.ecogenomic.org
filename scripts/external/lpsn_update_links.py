if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()


import os


from api.db import GtdbWebSession
from api.db.models import DbGtdbTree, GtdbWebUrlNcbi, GtdbWebUrlLpsn

import os
import re
from collections import defaultdict
from typing import Dict, Tuple
import sqlalchemy as sa
from bs4 import BeautifulSoup
from tqdm import tqdm

"""
1. Copy across the following files into a temporary directory:

mkdir -p /tmp/lpsn/files
zcp /srv/db/gtdb/metadata/release214/lpsn/phylum_list.lst /tmp/lpsn/files/phylum_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/class_list.lst /tmp/lpsn/files/class_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/order_list.lst /tmp/lpsn/files/order_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/family_list.lst /tmp/lpsn/files/family_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/genus_list.lst /tmp/lpsn/files/genus_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/species_list.lst /tmp/lpsn/files/species_list.tsv


"""

RANKS = ('phylum', 'class', 'order', 'family', 'genus', 'species')

LPSN_FILES = '/tmp/lpsn/files'

PATH_NO_MATCH = '/tmp/lpsn/no_match.tsv'
PATH_SQL = '/tmp/lpsn/run_me_sql.txt'

os.makedirs('/tmp/lpsn/', exist_ok=True)

PATH_LPSN = '/tmp/lpsn/full_data.tsv'

def read_gtdb_tree_table() -> Dict[str, Dict[str, Tuple[int, str]]]:
    """This is an export of the GTDB tree table from the GTDB website."""
    db = GtdbWebSession()
    try:
        query = sa.select([DbGtdbTree.id, DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome').where( DbGtdbTree.taxon != 'root')
        results = db.execute(query).fetchall()

        # Get those that already exist
        query2 = sa.select([GtdbWebUrlLpsn.id, GtdbWebUrlLpsn.url])
        results2 = db.execute(query2).fetchall()
        ids_in_db = {row.id: row.url for row in results2}

        out = defaultdict(dict)
        for row in results:
            if row.id not in ids_in_db:
                out[row.taxon] = row.id
        return out
    finally:
        db.close()

def read_lpsn_csv(path):
    out = dict()

    with open(path, 'r') as f:
        for line in f.readlines():
            _, taxon, url = line.strip().split('\t')
            url = url.replace('.de//', '.de/')
            out[taxon] = url
    return out

def parse_lpsn_file_all():
    out = defaultdict(dict)

    with open(PATH_LPSN, 'r') as f:
        header = f.readline().strip().split('\t')
        rank_idx = header.index('Rank')
        taxon_idx = header.index('Name')
        synonyms_idx = header.index('Synonyms')

        for line in f.readlines():
            cols = line.strip().split('\t')
            rank = cols[rank_idx]
            taxon = cols[taxon_idx]
            synonyms = cols[synonyms_idx]

            if taxon in out[rank]:
                raise Exception('Duplicate taxon')
            out[rank][taxon] = set(synonyms.split(','))
            if '' in out[rank][taxon]:
                out[rank][taxon].remove('')

    return out

def main():

    # d_synonyms = parse_lpsn_file_all()

    # Read the LPSN files urls
    urls = dict()
    for rank in RANKS:
        data = read_lpsn_csv(os.path.join(LPSN_FILES, f'{rank}_list.tsv'))
        urls[rank] = data

    # Read the data from the db
    gtdb_tree = read_gtdb_tree_table()

    # Match the rows
    no_match = list()
    run_sql = list()
    for rank in RANKS:
        for taxon, url in urls[rank].items():

            # Remove junk from the taxon name if it's not going to make it a duplicate
            new_taxon = taxon

            if taxon.startswith('Candidatus '):
                new_taxon = taxon.replace('Candidatus ', '')
                if new_taxon in urls[rank]:
                    new_taxon = taxon

            if taxon.startswith('[') and taxon.endswith(']'):
                new_taxon = taxon.replace('[', '').replace(']', '')
                if new_taxon in urls[rank]:
                    new_taxon = taxon

            taxon_with_prefix = f'{rank[0]}__{new_taxon}'

            gtdb_row = gtdb_tree.get(taxon_with_prefix)
            if gtdb_row is None:
                no_match.append(f'{rank}\t{taxon_with_prefix}\t{url}')
                found_extra_match = False
                #
                # # Check for synonyms
                # synonyms = d_synonyms[rank].get(taxon, set())
                # if len(synonyms) > 0:
                #     synonym_in_gtdb_tree = [f'{rank[0]}__{synonym}' for synonym in synonyms if f'{rank[0]}__{synonym}' in gtdb_tree]
                #
                #     if len(synonym_in_gtdb_tree) == 1:
                #         candidate_taxon_with_prefix = synonym_in_gtdb_tree[0]
                #
                #         if candidate_taxon_with_prefix[3:] not in urls[rank]:
                #             found_extra_match = True
                #             gtdb_row = gtdb_tree.get(candidate_taxon_with_prefix)
                #             taxon_with_prefix = candidate_taxon_with_prefix
                #         else:
                #             pass
                #
                # if not found_extra_match:
                #     no_match.append(f'{rank}\t{taxon_with_prefix}\t{url}')
                # else:
                #     run_sql.append(f"INSERT INTO gtdb_tree (lpsn_url) VALUES ('{url}') WHERE id = {gtdb_row};")
            else:
                run_sql.append(f"{gtdb_row}\t{url}")

    with open(PATH_NO_MATCH, 'w') as f:
        f.write('\n'.join(no_match))

    with open(PATH_SQL, 'w') as f:
        f.write('\n'.join(run_sql))

    print(f'No match: {len(no_match):,}')
    print(f'Run SQL @ {PATH_SQL}: {len(run_sql):,}')
    print(f'CLUSTER gtdb_tree_url_lpsn;')


    # https://lpsn.dsmz.de/domain/bacteria
    # https://lpsn.dsmz.de/domain/archaea

    return


if __name__ == '__main__':
    main()
