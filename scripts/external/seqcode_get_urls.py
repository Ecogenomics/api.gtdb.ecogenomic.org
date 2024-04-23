"""
This script will update the Common database with the latest SeqCode content.
"""

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import json
import multiprocessing as mp
import re
from pathlib import Path

import requests
import sqlalchemy as sa
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm

from api.db import GtdbCommonSession
from api.db.models import GtdbCommonSeqCodeHtmlQcWarnings, GtdbCommonSeqCodeHtmlChildren, GtdbCommonSeqCodeHtml
from api.util.collection import iter_batches

RE_PAGE_LINK = re.compile(r'<a class="page-link" href="\/seqcode\/names\?page=\d+">(\d+)<\/a>')
RE_NAME_HREF = re.compile(r'<a class="card-header-link" href="\/seqcode\/names\/(\d+)">')

N_CPUS = 15

RETRY = Retry(
    total=5,
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504]
)

# Set paths used throughout this script
ROOT = Path('/tmp/scrape/seqcode')
ROOT.mkdir(exist_ok=True, parents=True)

PATH_PAGES_DONE = ROOT / 'pages_done.tsv'
PATH_IDS_DONE = ROOT / 'ids_done.tsv'


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


def scrape_seqcode_page(page: int) -> tuple[int, set[int]]:
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


def get_seqcode_ids_from_db() -> set[int]:
    db = GtdbCommonSession()
    try:
        query = sa.text("SELECT id FROM seqcode_html;")
        results = db.execute(query).fetchall()
        return {x.id for x in results}
    finally:
        db.close()


def get_seqcode_ids_and_etag_from_db() -> dict[int, str | None]:
    db = GtdbCommonSession()
    try:
        query = sa.text("SELECT id, etag FROM seqcode_html;")
        results = db.execute(query).fetchall()
        return {x.id: x.etag for x in results}
    finally:
        db.close()


def get_seqcode_ids_and_content_from_db() -> dict[int, dict]:
    db = GtdbCommonSession()
    try:
        query = sa.text(
            "SELECT id, content FROM seqcode_html WHERE to_process=true AND content IS NOT NULL ORDER BY id;")
        results = db.execute(query).fetchall()
        return {x.id: json.loads(x.content) for x in results}
    finally:
        db.close()


def get_seqcode_ids():
    print('Obtaining SeqCode page IDs')

    # Read the database to find those IDs already processed
    existing_ids = get_seqcode_ids_from_db()
    print(f'Found {len(existing_ids):,} ids already in the database.')

    # Continue from previous execution
    if PATH_PAGES_DONE.exists():
        with PATH_PAGES_DONE.open() as f:
            page_ids_done = {int(x.strip()) for x in f.readlines()}
        print(f'Continuing from previous run with: {len(page_ids_done):,} pages already done.')
    else:
        page_ids_done = set()

    # Get the number of SeqCode pages to process
    n_pages = get_total_number_of_pages()

    # Remove those pages already processed
    page_ids_to_process = sorted(set(range(1, n_pages + 1)) - page_ids_done)

    # Process each page
    db = GtdbCommonSession()
    try:
        for page_id in tqdm(page_ids_to_process):

            # Get the IDs on the current page
            _, seqcode_ids = scrape_seqcode_page(page_id)

            if len(seqcode_ids) == 0:
                print(f'Error, unable to load page: {page_id}')
                continue

            # For each of the IDs found, create a new row within the database
            new_seqcode_ids = seqcode_ids - existing_ids
            if len(new_seqcode_ids) > 0:
                query_insert = []
                for cur_seqcode_id in sorted(new_seqcode_ids):
                    query_insert.append(f"({cur_seqcode_id}, true)")
                query_insert = ',\n'.join(query_insert) + ';'
                query = f'INSERT INTO seqcode_html (id, to_process)\nVALUES\n{query_insert}'
                db.execute(query)
                db.commit()

            # Save the page as done
            with PATH_PAGES_DONE.open('a') as f:
                f.write(f'{page_id}\n')

    finally:
        db.close()

    return


def get_seqcode_id_json(sc_id: int) -> tuple[int, str | None, dict]:
    try:
        out = dict()

        url = f'https://disc-genomics.uibk.ac.at/seqcode/names/{sc_id}.json'

        s = requests.Session()
        s.mount('https://', HTTPAdapter(max_retries=RETRY))
        r = s.get(url)

        if not r.ok:
            print(f'Failed to get {url}')
            return sc_id, None, out

        data = r.json()
        return sc_id, r.headers.get("ETag"), data
    except Exception:
        return sc_id, None, dict()


def process_seqcode_ids_single_batch(ids_in_batch, existing_ids):
    # Iterate over each page id and extract the content

    # Use multiple workers to pull in the page content
    with mp.Pool(processes=N_CPUS) as pool:
        results = list(pool.imap_unordered(get_seqcode_id_json, ids_in_batch))

    db = GtdbCommonSession()
    try:
        for sc_id, etag, payload in results:

            if not payload or len(payload) == 0:
                print(f'Unable to load info for page id: {sc_id}')
                continue

            # Compare the etag to see if an update should occur
            db_etag = existing_ids[sc_id]
            if db_etag != etag:
                query = f"UPDATE seqcode_html SET to_process=true, updated=CURRENT_TIMESTAMP, content=:content WHERE id=:sc_id;"
                db.execute(query, {'sc_id': sc_id, 'content': json.dumps(payload)})
                db.commit()

            # Save the result as successful
            with PATH_IDS_DONE.open('a') as f:
                f.write(f'{sc_id}\n')

    finally:
        db.close()
    return


def process_seqcode_ids():
    print('Processing SeqCode page IDs')

    # Read the database to find those IDs already processed
    existing_ids = get_seqcode_ids_and_etag_from_db()
    print(f'Found {len(existing_ids):,} ids already in the database.')

    # Continue from previous execution
    if PATH_IDS_DONE.exists():
        with PATH_IDS_DONE.open() as f:
            page_ids_done = {int(x.strip()) for x in f.readlines()}
        print(f'Continuing from previous run with: {len(page_ids_done):,} pages already done.')
    else:
        page_ids_done = set()

    # Set the page ids that need to be processed
    page_ids_to_process = sorted(set(existing_ids.keys()) - page_ids_done)
    batches = list(iter_batches(page_ids_to_process, n=100))

    for current_batch in tqdm(batches):
        process_seqcode_ids_single_batch(current_batch, existing_ids)


def update_qc_warnings(db, sc_id, qc_warnings):
    # Generate the delete query
    query_delete = (
        sa.delete(GtdbCommonSeqCodeHtmlQcWarnings)
        .where(GtdbCommonSeqCodeHtmlQcWarnings.sc_id == sc_id)
    )
    db.execute(query_delete)

    if qc_warnings and len(qc_warnings) > 0:
        # Generate the insert query
        insert = list()
        for warning in qc_warnings:
            rules = ';'.join(warning.get('rules', list()))
            rules = rules if rules else None
            insert.append(GtdbCommonSeqCodeHtmlQcWarnings(
                sc_id=sc_id,
                can_approve=warning.get('can_endorse'),
                text=warning['message'],
                rules=rules
            ))

        # Run the insert query
        db.add_all(insert)

    db.commit()

    return


def update_children(db, sc_id, children):
    query_delete = (
        sa.delete(GtdbCommonSeqCodeHtmlChildren)
        .where(GtdbCommonSeqCodeHtmlChildren.parent_id == sc_id)
    )
    db.execute(query_delete)

    if children and len(children) > 0:
        insert = list()
        for child in children:
            insert.append(GtdbCommonSeqCodeHtmlChildren(
                parent_id=sc_id,
                child_id=child['id']
            ))
        db.add_all(insert)

    db.commit()

    return


def update_seqcode_table(db, sc_id, payload):
    # Extract the rank information
    domain_id = None
    phylum_id = None
    class_id = None
    order_id = None
    family_id = None
    genus_id = None
    species_id = None
    for classification in payload.get('classification', list()):
        if classification['rank'] == 'domain':
            domain_id = classification['id']
        elif classification['rank'] == 'phylum':
            phylum_id = classification['id']
        elif classification['rank'] == 'class':
            class_id = classification['id']
        elif classification['rank'] == 'order':
            order_id = classification['id']
        elif classification['rank'] == 'family':
            family_id = classification['id']
        elif classification['rank'] == 'genus':
            genus_id = classification['id']
        elif classification['rank'] == 'species':
            species_id = classification['id']
        else:
            print(f'UNKNOWN RANK for id: {sc_id}')

    query = (
        sa.update(GtdbCommonSeqCodeHtml)
        .where(GtdbCommonSeqCodeHtml.id == sc_id)
        .values(
            to_process=False,
            name=payload.get('name'),
            rank=payload.get('rank'),
            status_name=payload.get('status_name'),
            syllabification=payload.get('syllabication'),
            priority_date=payload.get('priority_date'),
            formal_styling_raw=payload.get('formal_styling', dict()).get('raw'),
            formal_styling_html=payload.get('formal_styling', dict()).get('html'),
            etymology=payload.get('etymology'),
            sc_created_at=payload.get('created_at'),
            sc_updated_at=payload.get('updated_at'),
            domain_id=domain_id,
            phylum_id=phylum_id,
            class_id=class_id,
            order_id=order_id,
            family_id=family_id,
            genus_id=genus_id,
            species_id=species_id,
            corrigendum_by_id=payload.get('corrigendum_in', dict()).get('id'),
            corrigendum_by_citation=payload.get('corrigendum_in', dict()).get('citation'),
            corrigendum_from=payload.get('corrigendum_in', dict()).get('url'),
            description_raw=payload.get('description', dict()).get('raw'),
            proposed_by_id=payload.get('proposed_in', dict()).get('id'),
            proposed_by_citation=payload.get('proposed_in', dict()).get('citation'),
            notes_raw=payload.get('notes', dict()).get('raw'),
            notes_html=payload.get('notes', dict()).get('raw'),
        )
    )
    db.execute(query)
    db.commit()
    return


def maybe_create_new_ids(d_id_to_content):
    db_ids = get_seqcode_ids_from_db()
    ids_missing = set()
    for sc_id, payload in d_id_to_content.items():

        for classification in payload.get('classification', list()):
            if classification['id'] not in db_ids:
                ids_missing.add(classification['id'])

    db = GtdbCommonSession()
    try:
        insert = list()
        for missing_id in ids_missing:
            insert.append(GtdbCommonSeqCodeHtml(
                id=missing_id,
                to_process=False,
            ))
        db.add_all(insert)
        db.commit()
    finally:
        db.close()


def process_seqcode_content():
    print('Processing SeqCode content')
    d_id_to_content = get_seqcode_ids_and_content_from_db()
    print(f'Found {len(d_id_to_content):,} rows to process')

    maybe_create_new_ids(d_id_to_content)

    db = GtdbCommonSession()
    try:
        for sc_id, payload in tqdm(d_id_to_content.items()):
            # Update the qc warnings table
            update_qc_warnings(db, sc_id, payload.get('qc_warnings'))

            # Update the children table
            update_children(db, sc_id, payload.get('children'))

            # Update the seqcode_html table
            update_seqcode_table(db, sc_id, payload)

    finally:
        db.close()
    return


def main():
    """Run the application."""

    """
    First pass, obtain the SeqCode IDs present on the website and store
    them in the database.
    """
    get_seqcode_ids()

    """
    Second pass, load every SeqCode page and update the database with the current info
    """
    process_seqcode_ids()

    """
    Third pass, go through the database and find all with to_update=true and update
    the columns, plus additional tables if required
    """
    process_seqcode_content()


if __name__ == '__main__':
    main()
