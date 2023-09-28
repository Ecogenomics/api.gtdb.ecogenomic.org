from api.util.collection import iter_batches

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import hashlib
import os
import tempfile
from collections import defaultdict
from typing import Dict, Tuple

import requests
import sqlalchemy as sa
from tqdm import tqdm

from api.db import GtdbWebSession, GtdbCommonSession
from api.db.models import DbGtdbTree, GtdbCommonNcbiCitation, GtdbCommonNcbiName, GtdbCommonNcbiMergedNode, \
    GtdbCommonNcbiNode, GtdbCommonNcbiNodeCitation, GtdbCommonNcbiGencode, GtdbCommonNcbiDivision

PATH_TMP = '/tmp/taxdump'

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
        query = sa.select([DbGtdbTree.id, DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome').where(
            DbGtdbTree.taxon != 'root').where(DbGtdbTree.ncbi_taxid == None)
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
    if os.path.isdir(PATH_TMP):
        print(f'Already downloaded to {PATH_TMP}')
        return

    # Get the expected md5
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

        print('Untarring')
        os.makedirs(PATH_TMP, exist_ok=True)
        os.system(f'tar -xzf {path_gz_tmp} -C {PATH_TMP}')
    return


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


def iterate_over_ncbi_dump(path):
    with open(path) as f:
        content = f.read()
    content_lines = content.split('\t|\n')
    for line in tqdm(content_lines):
        cols = line.split('\t|\t')
        yield [x.strip() for x in cols]


def load_citations():
    db = GtdbCommonSession()
    query = sa.select([GtdbCommonNcbiCitation])
    results = db.execute(query).fetchall()
    out = dict()
    for row in results:
        out[row.cit_id] = dict(row)
    return out


def maybe_nullify(text):
    if text is None or text == '':
        return None
    return text


def parse_citations(path):
    print('Parsing citations')
    # existing = load_citations()

    citation_rows = list()
    taxid_rows = list()

    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue
        cit_id, cit_key, pubmed_id, medline_id, url, text, taxid_list = line

        pubmed_id = maybe_nullify(pubmed_id)
        medline_id = maybe_nullify(medline_id)

        # Additional parsing for text
        text = maybe_nullify(text)
        if text is not None:
            text = text.replace('\\\\n', '\n')  # newlines
            text = text.replace('\\n', '\n')  # newlines
            text = text.replace('\\t', '\t')  # tabs
            text = text.replace('\\"', '"')  # double quotes
            text = text.replace('\\\\', '\\')

        cur_citation_row = {
            'cit_id': int(cit_id),
            'cit_key': maybe_nullify(cit_key),
            'pubmed_id': int(pubmed_id) if pubmed_id is not None else None,
            'medline_id': int(medline_id) if medline_id is not None else None,
            'url': maybe_nullify(url),
            'content': text,
        }
        citation_rows.append(cur_citation_row)

        if taxid_list is not None and taxid_list != '':
            taxids = [int(x) for x in taxid_list.split(' ')]
            for taxid in taxids:
                cur_taxid_row = {
                    'cit_id': int(cit_id),
                    'tax_id': int(taxid),
                }
                taxid_rows.append(cur_taxid_row)

    return citation_rows, taxid_rows


def parse_delnodes(path):
    print('Parsing delnodes')
    out = set()
    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue
        out.add(int(line[0]))
    return out

def get_previous_division_rows():
    print('Loading existing rows from Division table')
    db = GtdbCommonSession()
    query = sa.select([
        GtdbCommonNcbiDivision.division_id,
        GtdbCommonNcbiDivision.cde,
        GtdbCommonNcbiDivision.name,
        GtdbCommonNcbiDivision.comments,
    ])
    results = db.execute(query).fetchall()
    out = dict()
    for row in results:
        out[row.division_id] = dict(row)
    return out

def parse_divsion(path):
    previous = get_previous_division_rows()

    print('Parsing division')
    out = list()
    n_skipped = 0
    total = 0
    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue
        total += 1

        division_id, cde, name, comments = line
        cur_row = {
            'division_id': int(division_id),
            'cde': maybe_nullify(cde),
            'name': maybe_nullify(name),
            'comments': maybe_nullify(comments),
        }

        prev_row = previous.get(cur_row['division_id'], None)
        if prev_row is None:
            out.append(cur_row)
        elif prev_row == cur_row:
            n_skipped +=1
        else:
            raise ValueError(f'Row mismatch: {prev_row} vs {cur_row}')

    print(f'Skipped {n_skipped:,} of {total:,} rows')
    return out


def load_previous_gencode_rows():
    print('Loading existing rows from GenCode table')
    db = GtdbCommonSession()
    query = sa.select([
        GtdbCommonNcbiGencode.gencode_id,
        GtdbCommonNcbiGencode.abbreviation,
        GtdbCommonNcbiGencode.name,
        GtdbCommonNcbiGencode.cde,
        GtdbCommonNcbiGencode.starts
    ])
    results = db.execute(query).fetchall()
    out = dict()
    for row in results:
        out[row.gencode_id] = dict(row)
    return out


def parse_gencode(path):
    previous = load_previous_gencode_rows()

    print('Parsing gencode')
    out = list()
    n_skipped = 0
    n_total = 0
    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue

        n_total += 1

        gencode_id, abbr, name, cde, starts = line
        cur_row = {
            'gencode_id': int(gencode_id),
            'abbreviation': maybe_nullify(abbr),
            'name': maybe_nullify(name),
            'cde': maybe_nullify(cde),
            'starts': maybe_nullify(starts),
        }

        prev_row = previous.get(cur_row['gencode_id'])

        if prev_row is None:
            out.append(cur_row)
        elif prev_row == cur_row:
            n_skipped += 1
        else:
            raise ValueError('Mismatched row')

    print(f'Skipped {n_skipped:,} ({n_skipped / n_total:.2%})')
    return out


def get_previous_merged_row():
    print('Loading existing rows from Merged table')
    db = GtdbCommonSession()
    query = sa.select([
        GtdbCommonNcbiMergedNode.old_tax_id,
        GtdbCommonNcbiMergedNode.new_tax_id,
    ])
    results = db.execute(query).fetchall()
    out = set()
    for row in results:
        out.add((row.old_tax_id, row.new_tax_id))
    return out

def parse_merged(path):
    previous = get_previous_merged_row()

    print('Parsing merged')
    out = list()
    n_skipped = 0
    n_total = 0
    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue
        old_taxid, new_taxid = line
        cur_row = {
            'old_tax_id': int(old_taxid),
            'new_tax_id': int(new_taxid),
        }
        n_total += 1
        if (cur_row['old_tax_id'], cur_row['new_tax_id']) not in previous:
            out.append(cur_row)
        else:
            n_skipped += 1
    print(f'Skipped {n_skipped:,} ({n_skipped / n_total:.2%})')
    return out

def get_previous_name_rows():
    print('Loading existing rows from Name table')
    db = GtdbCommonSession()
    query = sa.select([
        GtdbCommonNcbiName.tax_id,
        GtdbCommonNcbiName.name_txt,
        GtdbCommonNcbiName.unique_name,
        GtdbCommonNcbiName.name_class,
    ])
    results = db.execute(query).fetchall()
    out = dict()
    for row in results:
        out[row.tax_id] = dict(row)
    return out

def parse_names(path):
    prev_rows = get_previous_name_rows()

    print('Parsing names')
    out = list()
    seen = set()
    n_skipped, total = 0, 0
    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue
        if tuple(line) in seen:
            continue
        seen.add(tuple(line))

        tax_id, name_txt, unq_name, name_class = line
        cur_row = {
            'tax_id': int(tax_id),
            'name_txt': maybe_nullify(name_txt),
            'unique_name': maybe_nullify(unq_name),
            'name_class': maybe_nullify(name_class),
        }
        prev_row = prev_rows.get(int(tax_id), None)
        if prev_row is None:
            out.append(cur_row)
        elif prev_row == cur_row:
            n_skipped += 1
        else:
            raise ValueError('Mismatched row')
        total += 1

    print(f'Skipped {n_skipped:,} ({n_skipped / total:.2%})')
    return out


def maybe_to_boolean(x):
    if x == '':
        return None
    elif x == '1':
        return True
    elif x == '0':
        return False
    else:
        raise ValueError(f'Unknown boolean value: {x}')


def parse_nodes(path):
    print('Parsing nodes')
    out = list()
    out_parent = list()
    for line in iterate_over_ncbi_dump(path):
        if line == ['']:
            continue
        tax_id, parent_tax_id, rank, embl_code, div_id, div_flag, gencode_id, \
            gencode_flag, mito_gencode_id, mito_flag, genbank_hidden, \
            hidden_root, comments = line
        out.append({
            'tax_id': int(tax_id),
            'rank': maybe_nullify(rank),
            'embl_code': maybe_nullify(embl_code),
            'division_id': int(div_id),
            'inherited_div_flag': maybe_to_boolean(div_flag),
            'gencode_id': int(gencode_id),
            'inherited_gc_flag': maybe_to_boolean(gencode_flag),
            'mito_gencode_id': int(mito_gencode_id),
            'inherited_mgc_flag': maybe_to_boolean(mito_flag),
            'genbank_hidden': maybe_to_boolean(genbank_hidden),
            'hidden_subtree_root': maybe_to_boolean(hidden_root),
            'comments': maybe_nullify(comments),
        })
        out_parent.append({
            'tax_id': int(tax_id),
            'parent_tax_id': int(parent_tax_id),
        })
    return out, out_parent


def parse_ncbi_taxdump():
    path_citations = os.path.join(PATH_TMP, 'citations.dmp')
    path_delnodes = os.path.join(PATH_TMP, 'delnodes.dmp')
    path_division = os.path.join(PATH_TMP, 'division.dmp')
    path_gencode = os.path.join(PATH_TMP, 'gencode.dmp')
    path_merged = os.path.join(PATH_TMP, 'merged.dmp')
    path_names = os.path.join(PATH_TMP, 'names.dmp')
    path_nodes = os.path.join(PATH_TMP, 'nodes.dmp')

    gencode_rows = parse_gencode(path_gencode)
    division_rows = parse_divsion(path_division)
    merged_rows = parse_merged(path_merged)

    # TODO Check
    name_rows = parse_names(path_names)
    delnodes_rows = parse_delnodes(path_delnodes)
    citation_rows, name_citation_rows = parse_citations(path_citations)
    node_rows, node_rows_parent = parse_nodes(path_nodes)

    # Update the ncbi_node rows with the is_deleted flag
    print('Updating the is_deleted flag')
    for node_row in tqdm(node_rows):
        if node_row['tax_id'] in delnodes_rows:
            node_row['is_deleted'] = True
        else:
            node_row['is_deleted'] = False

    # 2. Insert the NCBI GenCode
    print('Inserting gencode')
    # insert_into_db(GtdbCommonNcbiGencode, gencode_rows)

    # 3. Insert the NCBI divisions
    print('Inserting division')
    # insert_into_db(GtdbCommonNcbiDivision, division_rows)

    # 4. Insert the NCBI citations
    print('Inserting ncbi_citation')
    # insert_into_db(GtdbCommonNcbiCitation, citation_rows)

    print('Inserting into ncbi_node')
    # insert_into_db(GtdbCommonNcbiNode, node_rows)
    # update_node_parent(node_rows_parent)

    print('Inserting into ncbi_merged_node')
    insert_into_db(GtdbCommonNcbiMergedNode, merged_rows)

    print('Inserting into ncbi_node_citation')
    insert_into_db(GtdbCommonNcbiNodeCitation, name_citation_rows)

    # 1. Insert the NCBI names
    print('Inserting names')
    insert_into_db(GtdbCommonNcbiName, name_rows)

    return


def insert_into_db(table, data):
    if len(data) == 0:
        print('No rows to insert')
        return
    db = GtdbCommonSession()
    batch_names = list(iter_batches(data, 1000))
    with tqdm(total=len(data)) as p_bar:
        for batch in batch_names:
            for row in batch:
                db.execute(sa.insert(table).values(**row))
                p_bar.update()
            db.commit()
    return


def update_node_parent(data):
    db = GtdbCommonSession()
    batch_names = list(iter_batches(data, 1000))
    with tqdm(total=len(data)) as p_bar:
        for batch in batch_names:
            for row in batch:
                query = sa.update(GtdbCommonNcbiNode).where(GtdbCommonNcbiNode.tax_id == row['tax_id']) \
                    .values(parent_tax_id=row['parent_tax_id'])
                db.execute(query)
                p_bar.update()
            db.commit()
    return


def main():
    # Read the NCBI taxdump
    download_ncbi_taxdump()
    parse_ncbi_taxdump()
    return


if __name__ == '__main__':
    main()
