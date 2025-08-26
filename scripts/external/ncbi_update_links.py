import tempfile

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import os

from api.db import GtdbWebSession
from api.db.models import DbGtdbTree, GtdbWebUrlNcbi
import requests

import os
import re
from collections import defaultdict
from typing import Dict, Tuple
import sqlalchemy as sa
from bs4 import BeautifulSoup
from tqdm import tqdm
import hashlib

"""
1. Copy across the following files into a temporary directory:

mkdir -p /tmp/lpsn/files
zcp /srv/db/gtdb/metadata/release214/lpsn/phylum_list.lst /tmp/lpsn/files/phylum_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/class_list.lst /tmp/lpsn/files/class_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/order_list.lst /tmp/lpsn/files/order_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/family_list.lst /tmp/lpsn/files/family_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/genus_list.lst /tmp/lpsn/files/genus_list.tsv
zcp /srv/db/gtdb/metadata/release214/lpsn/species_list.lst /tmp/lpsn/files/species_list.tsv

zcp /srv/db/gtdb/metadata/release214/lpsn/parse_html/all_ranks/full_parsing_parsed.tsv /tmp/lpsn/full_data.tsv

"""

RANKS = ('phylum', 'class', 'order', 'family', 'genus', 'species')

LPSN_FILES = '/tmp/lpsn/files'

PATH_NO_MATCH = '/tmp/lpsn/no_match.tsv'
PATH_SQL = '/tmp/lpsn/run_me_sql.txt'

URL_NCBI_TAXDUMP = 'https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz'
URL_NCBI_TAXDUMP_MD5 = 'https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz.md5'

os.makedirs('/tmp/ncbi', exist_ok=True)


def read_gtdb_tree_table() -> Dict[str, Dict[str, Tuple[int, str]]]:
    """This is an export of the GTDB tree table from the GTDB website."""
    db = GtdbWebSession()
    try:
        # Get the mapping
        query = sa.select([DbGtdbTree.id, DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome').where(
            DbGtdbTree.taxon != 'root')
        results = db.execute(query).fetchall()

        query2 = sa.select([GtdbWebUrlNcbi.id, GtdbWebUrlNcbi.taxid])
        results2 = db.execute(query2).fetchall()
        ids_in_db = {row.id: row.taxid for row in results2}

        out = defaultdict(dict)
        for row in results:
            if row.id not in ids_in_db:
                out[row.taxon] = row.id
        return out
    finally:
        db.close()


def download_ncbi_taxdump_md5():
    print('Getting MD5')
    r = requests.get(URL_NCBI_TAXDUMP_MD5)
    content = r.content.decode()
    return content.split(' ')[0]


def read_names(path):
    print('Reading names')
    out = dict()
    with open(path) as f:
        for line in tqdm(f.readlines(), total=3801979):
            cols = [x.strip() for x in line.strip().split('|')]
            if cols[3] == 'scientific name':
                out[int(cols[0])] = cols[1]
    return out


def read_nodes(path):
    print('Reading nodes')
    out = dict()
    with open(path) as f:
        for line in tqdm(f.readlines(), total=2_497_435):
            cols = [x.strip() for x in line.strip().split('|')]
            # prok only
            if cols[4] == '0':
                out[int(cols[0])] = cols[2]
    return out


def download_ncbi_taxdump():
    expected_md5 = download_ncbi_taxdump_md5()

    # Download the file
    with tempfile.TemporaryDirectory() as tmp_dir:
        path_gz_tmp = os.path.join(tmp_dir, 'taxdump.tar.gz')

        print('Downloading NCBI taxdump')
        with open(path_gz_tmp, 'wb') as f:
            r = requests.get(URL_NCBI_TAXDUMP)
            f.write(r.content)

        # Check the md5
        print('Checking MD5')
        md5 = hashlib.md5()
        with open(path_gz_tmp, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        actual_md5 = md5.hexdigest()

        if actual_md5 != expected_md5:
            raise Exception('Corrupted file!')

        # Untar the file
        print('Untarring')
        os.system(f'tar -xzf {path_gz_tmp} -C {tmp_dir}')

        path_names = os.path.join(tmp_dir, 'names.dmp')
        path_nodes = os.path.join(tmp_dir, 'nodes.dmp')

        d_names = read_names(path_names)
        d_nodes = read_nodes(path_nodes)

        print('Merging data')
        out = dict()
        for taxid, names in tqdm(d_names.items(), total=len(d_names)):
            if taxid not in d_nodes:
                continue
            rank = d_nodes[taxid]
            out[taxid] = (rank, names)
        return out


def remove_suprious_names(d_ncbi_data, d_gtdb_tree):
    gtdb_taxa_no_prefix = {x[3:] for x in d_gtdb_tree.keys()}
    gtdb_taxa_prefix = {x for x in d_gtdb_tree.keys()}
    gtdb_taxa = gtdb_taxa_prefix.union(gtdb_taxa_no_prefix)
    out = dict()
    n_matched, n_missing = 0, 0
    for taxid, (rank, name) in tqdm(d_ncbi_data.items(), total=len(d_ncbi_data)):
        if name in gtdb_taxa:
            if name in out:
                print('??')
            out[name] = (rank, taxid)
            n_matched += 1
        else:
            n_missing += 1
    print(f'Matched: {n_matched:,}')
    print(f'Missing: {n_missing:,}')
    return out


def main():
    # Read the NCBI taxdump
    d_ncbi_data = download_ncbi_taxdump()

    # Read the data from the db
    d_gtdb_tree = read_gtdb_tree_table()

    # Match the data
    print('Removing suprious names from NCBI')
    d_ncbi_taxon_to_rank_and_taxid = remove_suprious_names(d_ncbi_data, d_gtdb_tree)

    to_sql_write = list()

    for ncbi_taxon, (ncbi_rank, ncbi_taxid) in d_ncbi_taxon_to_rank_and_taxid.items():

        if ncbi_rank == 'superkingdom':
            ncbi_taxon_prefixed = f'd__{ncbi_taxon}'
        elif ncbi_rank == 'subclass':
            ncbi_taxon_prefixed = f'c__{ncbi_taxon}'
        else:
            ncbi_taxon_prefixed = f'{ncbi_rank[0]}__{ncbi_taxon}'

        gtdb_id = d_gtdb_tree[ncbi_taxon_prefixed]

        to_sql_write.append(f'{gtdb_id}\t{ncbi_taxid}')

    with open('/tmp/ncbi_import.txt', 'w') as f:
        f.write('\n'.join(to_sql_write))

    print(f'Import the contents of /tmp/ncbi_import.txt into the gtdb_tree_url_ncbi table.')
    print('CLUSTER gtdb_tree_url_ncbi;')

    return


if __name__ == '__main__':
    main()
