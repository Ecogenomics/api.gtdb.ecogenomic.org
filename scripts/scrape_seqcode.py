if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import json
import multiprocessing as mp
import os
import re
from collections import defaultdict
from typing import Dict, Tuple

import requests
import sqlalchemy as sa
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm

from api.db import GtdbWebSession
# from api.db.models import DbGtdbTree

RE_PAGE_LINK = re.compile(r'<a class="page-link" href="\/seqcode\/names\?page=\d+">(\d+)<\/a>')
RE_NAME_HREF = re.compile(r'<a class="card-header-link" href="\/seqcode\/names\/(\d+)">')

N_CPUS = 15

RETRY = Retry(total=5,
              backoff_factor=0.1,
              status_forcelist=[500, 502, 503, 504])

ROOT = '/tmp/seqcode'
os.makedirs(ROOT, exist_ok=True)


def read_gtdb_tree_table() -> Dict[str, Dict[str, Tuple[int, str]]]:
    """This is an export of the GTDB tree table from the GTDB website."""
    db = GtdbWebSession()
    try:
        query = sa.select([DbGtdbTree.id, DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome').where(
            DbGtdbTree.taxon != 'root')
        results = db.execute(query).fetchall()

        out = defaultdict(dict)
        for row in results:
            out[row.taxon] = row.id
        return dict(out)
    finally:
        db.close()


def get_total_number_of_pages():
    r = requests.get('https://disc-genomics.uibk.ac.at/seqcode/names')

    if not r.ok:
        raise Exception('Failed to get page')

    html = r.text.replace('\n', '')

    matches = RE_PAGE_LINK.findall(html)

    if not matches:
        raise Exception('Failed to find page links')

    last_page = max((int(x) for x in matches))
    print(f'Found {last_page:,} pages')
    return last_page


def get_names_from_page_worker(page: int):
    url = f'https://disc-genomics.uibk.ac.at/seqcode/names?page={page}'

    try:

        s = requests.Session()
        s.mount('https://', HTTPAdapter(max_retries=RETRY))
        r = s.get(url)

        out = set()

        if not r.ok:
            print(f'Unable to get from page: {page:,}')
            return page, out

        html = r.text.replace('\n', '')
        matches = RE_NAME_HREF.findall(html)

        if not matches:
            print(f'Unable to find names on page: {page:,}')
            return page, out

        # Found hits
        out.update([int(x) for x in matches])
        return page, out
    except Exception:
        return page, set()


def process_seqcode_id(sc_id: int):
    try:
        out = dict()

        url = f'https://disc-genomics.uibk.ac.at/seqcode/names/{sc_id}.json'

        s = requests.Session()
        s.mount('https://', HTTPAdapter(max_retries=RETRY))
        r = s.get(url)

        if not r.ok:
            print(f'Failed to get {url}')
            return sc_id, out

        data = r.json()
        return sc_id, data
    except Exception:
        return sc_id, dict()


def process_all_seqcode_pages():
    # Perform the initial page load
    n_pages = get_total_number_of_pages()

    # Create a queue for each page
    queue = list(range(1, n_pages + 1))

    # Process each page in a queue
    pages_not_completed = set()
    pages_completed = set()
    seqcode_ids = set()
    with mp.Pool(processes=N_CPUS) as pool:
        for cur_page_no, cur_seqcode_ids in list(
                tqdm(pool.imap_unordered(get_names_from_page_worker, queue, chunksize=3), total=len(queue))):
            if len(cur_seqcode_ids) > 0:
                pages_completed.add(cur_page_no)
                seqcode_ids.update(cur_seqcode_ids)
            else:
                pages_not_completed.add(cur_page_no)

    if len(pages_not_completed) > 0:
        path_fail_pages = os.path.join(ROOT, '1_seqcode_pages_failed.tsv')
        print(f'There were {len(pages_not_completed):,} pages that failed to load')
        print(f'These were saved to: {path_fail_pages}')
        with open(path_fail_pages, 'w') as f:
            f.write('\n'.join(map(str, sorted(pages_not_completed))))

    # Using the results from each page, load the page content for each name
    seqcode_ids_ok = set()
    seqcode_ids_fail = set()
    seqcode_data = dict()
    with mp.Pool(processes=N_CPUS) as pool:
        for cur_sc_id, cur_data in list(
                tqdm(pool.imap_unordered(process_seqcode_id, seqcode_ids, chunksize=3), total=len(seqcode_ids))):
            if len(cur_data) > 0:
                seqcode_ids_ok.add(cur_sc_id)
                seqcode_data[cur_sc_id] = cur_data
            else:
                seqcode_ids_fail.add(cur_sc_id)

    if len(seqcode_ids_fail) > 0:
        path_fail_ids = os.path.join(ROOT, '2_seqcode_ids_failed.tsv')
        print(f'There were {len(seqcode_ids_fail):,} seqcode ids that failed to load')
        print(f'These were saved to: {path_fail_ids}')
        with open(path_fail_ids, 'w') as f:
            f.write('\n'.join(map(str, sorted(seqcode_ids_fail))))

    return seqcode_data


def main():
    path_db = os.path.join(ROOT, '0_seqcode_data.tsv')
    if os.path.isfile(path_db):
        sc_data = dict()
        with open(path_db, 'r') as f:
            for line in f.readlines():
                sc_id, sc_json = line.strip().split('\t|\t')
                sc_data[int(sc_id)] = json.loads(sc_json)
    else:
        # Read the pages from SeqCode
        sc_data = process_all_seqcode_pages()

        with open(path_db, 'w') as f:
            for sc_id, sc_json in sc_data.items():
                f.write(f'{sc_id}\t|\t{json.dumps(sc_json)}\n')

    # Read the data from the GTDB tree table
    gtdb_tree = read_gtdb_tree_table()

    # Match the names
    sc_failed = dict()
    sc_no_match = dict()
    sc_matched = dict()
    rows = list()
    ranks_seen = set()
    for sc_id, sc_json in tqdm(sc_data.items()):
        try:
            sc_name = sc_json['name']
            sc_rank = sc_json['rank']
            extra = False
            ranks_seen.add(sc_rank)

            if sc_name.startswith('Candidatus'):
                sc_name = sc_name.replace('Candidatus ', '')

            if sc_rank is None:
                if ' ' in sc_name:
                    sc_rank = 'species'
                elif sc_name in {'Piscichlamydia', 'Alkanophaga', 'Electronema', 'Lariskella'}:
                    sc_rank = 'genus'
                    extra = True
                elif sc_name in {'Nealsonbacteria', 'Izemoplasmatales', 'Roizmanbacteria', 'Absconditabacteria', 'Patescibacteria'}:
                    sc_rank = 'class'
                    extra = True
                elif sc_name in {'Nanohaloarchaeota'}:
                    sc_rank = 'phylum'
                    extra = True
                elif sc_name in {'Eudoremicrobiaceae'}:
                    sc_rank = 'family'
                    extra = True
                else:
                    print(f'https://seqco.de/n:{sc_name}', sc_name)
                    continue

            sc_taxon = f'{sc_rank[0]}__{sc_name}'

            gtdb_hit = gtdb_tree.get(sc_taxon)
            if gtdb_hit is None:
                sc_no_match[sc_id] = sc_json
            else:
                sc_matched[sc_id] = sc_json
                url = f'https://seqco.de/n:{sc_name.replace(" ", "_")}'
                rows.append(f"UPDATE gtdb_tree SET seqcode_url='{url}' WHERE id={gtdb_hit};\n")

                if extra:
                    print(f"UPDATE gtdb_tree SET seqcode_url='{url}' WHERE id={gtdb_hit};")

        except Exception:
            print('exception')
            sc_failed[sc_id] = sc_json

    print(f'Ranks seen: {ranks_seen}')
    if len(sc_failed) > 0:
        path_fail_ids = os.path.join(ROOT, '3_seqcode_parse_ids_failed.tsv')
        print(f'There were {len(sc_failed):,} seqcode ids that failed to load')
        print(f'These were saved to: {path_fail_ids}')
        with open(path_fail_ids, 'w') as f:
            f.write('\n'.join([json.dumps(x) for x in sc_failed.values()]))

    if len(sc_no_match) > 0:
        path_fail_ids = os.path.join(ROOT, '4_seqcode_parse_ids_no_match.tsv')
        print(f'There were {len(sc_no_match):,} seqcode ids that failed to load')
        print(f'These were saved to: {path_fail_ids}')
        with open(path_fail_ids, 'w') as f:
            f.write('\n'.join([json.dumps(x) for x in sc_no_match.values()]))

    if len(sc_matched) > 0:
        path_fail_ids = os.path.join(ROOT, '5_seqcode_parse_ids_matched.tsv')
        print(f'There were {len(sc_matched):,} seqcode ids that matched')
        print(f'These were saved to: {path_fail_ids}')
        with open(path_fail_ids, 'w') as f:
            f.write('\n'.join([json.dumps(x) for x in sc_matched.values()]))

    if len(rows) > 0:
        path_rows_out = os.path.join(ROOT, '6_output_sql.tsv')
        print(f'There were {len(rows):,} rows to update')
        print(f'These were saved to: {path_rows_out}')
        with open(path_rows_out, 'w') as f:
            f.write('\n'.join(rows))
    return


if __name__ == '__main__':
    main()
