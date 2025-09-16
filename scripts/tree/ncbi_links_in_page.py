import json
import tempfile

from api.util.collection import iter_batches

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()


import os


from api.db import GtdbWebSession, GtdbSession
# from api.db.models import DbGtdbTree, Genome, MetadataTaxonomy, GtdbWebGenomeTaxId
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
        query = sa.select([DbGtdbTree.id, DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome').where( DbGtdbTree.taxon != 'root').where(DbGtdbTree.ncbi_taxid == None)
        results = db.execute(query).fetchall()

        out = defaultdict(dict)
        for row in results:
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
    banned_names = set()
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

            if rank == 'domain':
                name_parsed = f'd__{names}'
            elif rank == 'phylum':
                name_parsed = f'p__{names}'
            elif rank == 'class':
                name_parsed = f'c__{names}'
            elif rank == 'order':
                name_parsed = f'o__{names}'
            elif rank == 'family':
                name_parsed = f'f__{names}'
            elif rank == 'genus':
                name_parsed = f'g__{names}'
            elif rank == 'species':
                name_parsed = f's__{names}'
            else:
                name_parsed = f'x__{names}'

            if name_parsed in banned_names:
                continue

            if name_parsed in out and str(taxid) != out[name_parsed]:
                print(f'Deleting: {name_parsed} {out[name_parsed]} {taxid}')
                del out[name_parsed]
                banned_names.add(name_parsed)
            out[name_parsed] = str(taxid)
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

def read_previous_release_dump():
    path = '/tmp/genome_taxid.tsv'
    out = dict()
    with open(path) as f:
        for line in tqdm(f.readlines()):
            gid, payload = line.strip().split('\t')
            if payload == '{}':
                continue
            payload = json.loads(payload.strip()[1:-1].replace('""', '"'))
            for taxon, taxid in payload.items():
                out[taxon] = taxid
    return out

def read_from_gids():
    db = GtdbSession()
    query = sa.select([Genome.name, MetadataTaxonomy.ncbi_taxonomy, MetadataTaxonomy.ncbi_taxonomy_unfiltered]).join(MetadataTaxonomy, MetadataTaxonomy.id == Genome.id)
    results = db.execute(query).fetchall()

    out = dict()
    for result in tqdm(results):
        out[result.name] = dict(result)
    return out

def main():

    d_gids = read_from_gids()

    d_ncbi_previous = read_previous_release_dump()

    # Read the NCBI taxdump
    d_ncbi_data = download_ncbi_taxdump()

    rows = list()
    for gid, d_info in tqdm(d_gids.items()):
        cur_values = dict()
        for rank in d_info['ncbi_taxonomy'].split(';'):
            if len(rank) == 3:
                continue
            if rank in d_ncbi_previous:
                taxid = d_ncbi_previous[rank]
            elif rank in d_ncbi_data:
                taxid = d_ncbi_data[rank]
            else:
                print(f'No match for {gid} {rank}')
                continue
            cur_values[rank] = taxid
        for rank in d_info['ncbi_taxonomy_unfiltered'].split(';'):
            if len(rank) == 3:
                continue
            if rank in d_ncbi_previous:
                taxid = d_ncbi_previous[rank]
            elif rank in d_ncbi_data:
                taxid = d_ncbi_data[rank]
            else:
                print(f'No match for {gid} {rank}')
                continue
            if rank in cur_values and cur_values[rank] != taxid:
                print(f'Overwriting {gid} {rank} {cur_values[rank]} {taxid}')
            cur_values[rank] = taxid
        rows.append((gid, cur_values))

    db = GtdbWebSession()
    batches = list(iter_batches(rows, 1000))
    for batch in tqdm(batches, total=len(batches)):
        for item in batch:
            obj = sa.insert(GtdbWebGenomeTaxId).values(genome_id=item[0], payload=item[1])
            db.execute(obj)
        db.commit()






    return


if __name__ == '__main__':
    main()
