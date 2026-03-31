if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()


import os
from api.db import gtdb_web_engine
from sqlmodel import Session
import re

import os
from collections import defaultdict
from typing import Dict, Tuple
import sqlalchemy as sa
from api.db.gtdb_web import DbGtdbTree, DbGtdbTreeUrlLpsn

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

LPSN_FILES = '/Users/aaron/tmp/lpsn'

PATH_NO_MATCH = '/tmp/lpsn/no_match.tsv'
PATH_SQL = '/tmp/lpsn/run_me_sql.txt'

os.makedirs('/tmp/lpsn/', exist_ok=True)

PATH_LPSN = '/tmp/lpsn/full_data.tsv'

def read_gtdb_tree_table() :
    """This is an export of the GTDB tree table from the GTDB website."""
    with Session(gtdb_web_engine) as db:
        try:

            # Obtain the list of taxa in the tree
            query = (
                sa.select(DbGtdbTree.id, DbGtdbTree.taxon)
                .where(DbGtdbTree.type != 'genome')
                 .where( DbGtdbTree.taxon != 'root')
                 )
            taxa_list = db.execute(query).fetchall()

            # Obtain the list of taxa in the tree that already have an LPSN URL
            query2 = (sa.select(DbGtdbTreeUrlLpsn.id, DbGtdbTreeUrlLpsn.url))
            lpsn_id_list = db.execute(query2).fetchall()
            ids_in_db = {row.id: row.url for row in lpsn_id_list}

            out_missing = dict()
            out_exists = dict()
            for row in taxa_list:
                if row.id not in ids_in_db:
                    out_missing[row.taxon] = row.id
                else:
                    out_exists[row.taxon] = row.id
            return out_missing, out_exists
        finally:
            db.close()

RE_NUMBERED_NAME = re.compile(r'.+-(\d+)')

def read_lpsn_csv(path):
    out = dict()
    is_species = 'species' in path

    with open(path, 'r') as f:
        lines = set(f.readlines())

    # Sort the lines by the URL
    lines = sorted(lines, key=lambda x: x.strip().split('\t')[2])

    for line in lines:

        # Extract columns
        _, taxon, url = line.strip().split('\t')

        # Correct double-slashes in URL if present
        url = url.replace('.de//', '.de/')

        # For species, we want to extract the binomial name from the URL
        if is_species:
            url_taxon = url.split('/')[-1]
            url_taxon_split = url_taxon.split('-')
            url_taxon_binomial = f'{url_taxon_split[0].capitalize()} {url_taxon_split[1]}'

            # We want to keep this only if the non-numbered didn't match or doesn't exist
            # this is guaranteed based on the sorting previously done
            if RE_NUMBERED_NAME.match(url_taxon):
                if url_taxon_binomial not in out:
                    out[url_taxon_binomial] = url
                # else:
                #     print(f'Skipping {url_taxon_binomial} because {url_taxon} already exists in {path}.')
            else:
                if url_taxon_binomial in out:
                    print(f'WARNING: Duplicate taxon {url_taxon_binomial} ({url}) in {path}.')
                out[url_taxon_binomial] = url

        # Attempt to extract the taxon name from the URL and validate against taxon column
        else:
            url_taxon = url.split('/')[-1].capitalize()

            # We want to keep this only if the non-numbered didn't match or doesn't exist
            # this is guaranteed based on the sorting previously done
            if RE_NUMBERED_NAME.match(url_taxon):
                stripped_taxon = url_taxon.split('-')[0]
                if stripped_taxon not in out:
                    url_taxon = stripped_taxon
                    out[url_taxon] = url
                # else:
                #     print(f'Skipping {url_taxon} because {stripped_taxon} already exists in {path}.')
            else:
                if url_taxon not in out:
                    out[url_taxon] = url
                else:
                    print(f'WARNING: Duplicate taxon {url_taxon} ({url}) in {path}.')
    return out
#
# def parse_lpsn_file_all():
#     out = defaultdict(dict)
#
#     with open(PATH_LPSN, 'r') as f:
#         header = f.readline().strip().split('\t')
#         rank_idx = header.index('Rank')
#         taxon_idx = header.index('Name')
#         synonyms_idx = header.index('Synonyms')
#
#         for line in f.readlines():
#             cols = line.strip().split('\t')
#             rank = cols[rank_idx]
#             taxon = cols[taxon_idx]
#             synonyms = cols[synonyms_idx]
#
#             if taxon in out[rank]:
#                 raise Exception('Duplicate taxon')
#             out[rank][taxon] = set(synonyms.split(','))
#             if '' in out[rank][taxon]:
#                 out[rank][taxon].remove('')
#
#     return out



def main():

    # d_synonyms = parse_lpsn_file_all()

    # Read the LPSN files urls
    print('Parsing LPSN files')
    urls = dict()
    for rank in RANKS:
        data = read_lpsn_csv(os.path.join(LPSN_FILES, f'{rank}_list.tsv'))
        urls[rank] = data

    # Read the data from the db
    print('Obtaining data from GTDB tree table')
    taxon_to_id_missing, taxon_to_id_exists = read_gtdb_tree_table()

    # Match the rows over each rank
    print('Matching rows')
    no_match = list()
    already_in_db = list()
    run_sql = list()
    new_taxa = set()
    for rank in RANKS:
        for taxon, url in urls[rank].items():
            taxon_with_prefix = f'{rank[0]}__{taxon}'


            # Do we already have this taxon in the tree?
            if taxon_with_prefix in taxon_to_id_exists:
                existing_id = taxon_to_id_exists[taxon_with_prefix]
                already_in_db.append(f'{rank}\t{taxon_with_prefix}\t{url} = {existing_id}')

                # Nothing to do
                continue

            # Otherwise, we want to add this taxon to the tree (if it's a GTDB taxon)
            if taxon_with_prefix in taxon_to_id_missing:
                gtdb_tree_id = taxon_to_id_missing[taxon_with_prefix]
                run_sql.append(f"{gtdb_tree_id}\t{url}")

            # This is not a GTDB taxon
            else:
                no_match.append(f'{rank}\t{taxon_with_prefix}\t{url}')

    with open(PATH_NO_MATCH, 'w') as f:
        f.write('\n'.join(no_match))

    with open(PATH_SQL, 'w') as f:
        f.write('\n'.join(run_sql))

    print(f'No match: {len(no_match):,}')
    print(f'Already in db: {len(already_in_db):,}')
    print(f'Run SQL @ {PATH_SQL}: {len(run_sql):,}')
    print(f'CLUSTER gtdb_tree_url_lpsn;')


    # https://lpsn.dsmz.de/domain/bacteria
    # https://lpsn.dsmz.de/domain/archaea

    return


if __name__ == '__main__':
    main()
