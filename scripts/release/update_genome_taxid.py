if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict

import requests
import sqlalchemy as sa
from tqdm import tqdm

from api.db import GtdbWebSession, GtdbSession, GTDB_DB_URL, GTDB_WEB_DB_URL
from api.db.models import Genome, MetadataTaxonomy, GtdbWebGenomeTaxId
from api.util.collection import iter_batches

# Configuration
RANKS = ('domain', 'phylum', 'class', 'order', 'family', 'genus', 'species')
WORKING_DIR = '/tmp/update_genome_taxids'
PATH_TAXDUMP_PROCESSED = os.path.join(WORKING_DIR, 'taxdump.json')

URL_NCBI_TAXDUMP = 'https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz'
URL_NCBI_TAXDUMP_MD5 = 'https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz.md5'


def read_from_gids():
    db = GtdbSession()
    query = sa.select([Genome.name, MetadataTaxonomy.ncbi_taxonomy, MetadataTaxonomy.ncbi_taxonomy_unfiltered]).join(
        MetadataTaxonomy, MetadataTaxonomy.id == Genome.id)
    results = db.execute(query).fetchall()

    out = dict()
    for result in tqdm(results):
        out[result.name] = dict(result)
    return out


def confirm_database_selection():
    gtdb_db = GTDB_DB_URL.split('/')[-1]
    web_db = GTDB_WEB_DB_URL.split('/')[-1]

    response = input(f'Using GTDB {gtdb_db}, writing to {web_db}. Is this OK? (Y/N)')
    if response.upper() != 'Y':
        print('Exiting.')
        sys.exit(1)
    print()


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
    os.makedirs(WORKING_DIR, exist_ok=True)

    if os.path.isfile(PATH_TAXDUMP_PROCESSED):
        with open(PATH_TAXDUMP_PROCESSED) as f:
            return json.load(f)

    expected_md5 = download_ncbi_taxdump_md5()
    banned_names = set()

    path_taxdump = os.path.join(WORKING_DIR, 'taxdump.tar.gz')

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

        print('Writing to disk')
        with open(PATH_TAXDUMP_PROCESSED, 'w') as f:
            json.dump(out, f)
        return out


def generate_new_tuples(d_gids, d_taxon_mapping):
    # Iterate over the genomes from the new release and get the taxon ids
    rows = list()
    for gid, d_info in tqdm(d_gids.items()):
        cur_row = dict()
        for cur_set in ('ncbi_taxonomy', 'ncbi_taxonomy_unfiltered'):
            for taxon in d_info[cur_set].split(';'):
                cur_tax_id = d_taxon_mapping.get(taxon)
                if cur_tax_id is not None:
                    cur_row[taxon] = cur_tax_id
        rows.append((gid, cur_row))
    return rows


def get_taxon_mapping(d_gids, d_ncbi_data):
    taxa = set()
    for gid, d_info in d_gids.items():
        for cur_set in ('ncbi_taxonomy', 'ncbi_taxonomy_unfiltered'):
            cur_tax_string = d_info[cur_set]
            taxa.update(cur_tax_string.split(';'))

    out = dict()
    no_mapping = set()
    duplicate = defaultdict(set)

    for taxon in taxa:
        tax_id = d_ncbi_data.get(taxon)

        if tax_id is None:
            if taxon == 'd__Bacteria':
                out[taxon] = d_ncbi_data['x__Bacteria']
            elif taxon == 'd__Archaea':
                out[taxon] = d_ncbi_data['x__Archaea']
            else:
                no_mapping.add(taxon)

        elif tax_id in out and out[taxon] != tax_id:
            duplicate[taxon].add(tax_id)
            duplicate[taxon].add(out[taxon])

        else:
            out[taxon] = tax_id

    if len(duplicate) > 0:
        print('WARNING, there were duplicates.')
    if len(no_mapping) > 0:
        print(f'Unable to find a mapping for {len(no_mapping):,} taxa.')
    return out


def insert_rows(rows):
    db = GtdbWebSession()
    batches = list(iter_batches(rows, 1000))
    for batch in tqdm(batches, total=len(batches)):
        for item in batch:
            obj = sa.insert(GtdbWebGenomeTaxId).values(genome_id=item[0], payload=item[1])
            db.execute(obj)
        db.commit()
    return


def main():
    # Confirm this is the correct database
    confirm_database_selection()

    print('Downloading the NCBI taxdump')
    d_ncbi_data = download_ncbi_taxdump()

    print('Collecting genomes from new GTDB release')
    d_gids = read_from_gids()

    print('Getting a mapping for each unique taxon')
    d_taxon_mapping = get_taxon_mapping(d_gids, d_ncbi_data)

    print('Generating new tuples')
    rows = generate_new_tuples(d_gids, d_taxon_mapping)

    print('Inserting rows')
    insert_rows(rows)

    return


if __name__ == '__main__':
    main()
