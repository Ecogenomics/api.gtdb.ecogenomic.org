"""
This script will update the Common database with the latest SeqCode content.
"""

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

import requests
from requests.adapters import Retry
from tqdm import tqdm

N_CPUS = 15

RETRY = Retry(
    total=5,
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504]
)

SEQCODE_INDEX_URL = "https://api.seqco.de/v1/names.json"
SEQCODE_BACTERIA_ID = 753
SEQCODE_ARCHAEA_ID = 754


def get_seqcode_index_page(page_no: int):
    """This method will parse a single SeqCode index page and return the JSON data."""
    r = requests.get(SEQCODE_INDEX_URL, params={'page': page_no, 'status': 'public'})
    if not r.ok:
        print(f'Failed to fetch SeqCode index page {page_no}: {r.status_code} {r.reason}')
        return None
    return r.json()


def get_n_seqcode_index_pages():
    """This method will parse the first page to get the number of pages available."""
    page = get_seqcode_index_page(1)
    if not page:
        raise ValueError("Failed to parse the first SeqCode index page.")
    return int(page['response']['total_pages'])


def scrape_index_pages_worker(job):
    """This method will scrape a single SeqCode index page and save the data to a file."""
    page_no, directory = job
    page = get_seqcode_index_page(page_no)
    if page:
        out_path = directory / f'page_{page_no}.json'
        with out_path.open('w') as f:
            f.write(json.dumps(page))
        return False
    return True


def scrape_index_pages(directory: Path, n_cpus: int):
    """
    The main method for scraping SeqCode index pages.

    This will begin by finding out how many pages there are and then distributing them across multiple CPUs.
    """
    n_pages = get_n_seqcode_index_pages()
    print(f'Found {n_pages:,} SeqCode index pages to scrape.')

    # Check what pages have already been scraped
    existing_files = list(directory.glob('page_*.json'))
    existing_page_numbers = set()
    for file in existing_files:
        existing_page_numbers.add(int(file.stem.split('page_')[-1]))
    print(f'Found {len(existing_page_numbers):,} existing SeqCode index pages.')

    has_error = False
    with mp.Pool(n_cpus) as pool:
        # Create a list of page numbers to scrape
        page_numbers = set(range(1, n_pages + 1))
        page_numbers -= existing_page_numbers
        queue = [(page_no, directory) for page_no in sorted(page_numbers)]

        # Use tqdm to show progress
        for is_error in tqdm(pool.imap_unordered(scrape_index_pages_worker, queue), initial=len(existing_page_numbers),
                             total=n_pages):
            has_error = has_error or is_error

    if has_error:
        print('Some SeqCode index pages failed to scrape. Please check the logs.')
        sys.exit(1)

    return


def extract_names_from_pages(index_dir: Path, out_path: Path):
    """This method will extract names from the SeqCode index pages and save them to a file."""
    index_files = list(index_dir.glob('page_*.json'))
    data = dict()
    for file_name in tqdm(index_files):
        with file_name.open('r') as f:
            page_data = json.load(f)
            for value in page_data['values']:
                data[value['id']] = (value['name'], value['url'], value['uri'])

    # Write the data to a file
    with out_path.open('w') as f:
        f.write('id\tname\turl\turi\n')
        for uid, (name, url, uri) in sorted(data.items()):
            f.write(f'{uid}\t{name}\t{url}\t{uri}\n')
    return


def scrape_name_id_page(url):
    """This method will scrape a single SeqCode name page by its ID."""
    r = requests.get(url)
    if not r.ok:
        print(f'Failed to fetch SeqCode page {url}: {r.status_code} {r.reason}')
        return None
    return r.json()


def scrape_name_page_worker(job):
    """This method will scrape a single SeqCode name page and save the data to a file."""
    uid, url, dir_names = job
    data = scrape_name_id_page(url)
    if data:
        out_path = dir_names / f'name_{uid}.json'
        with out_path.open('w') as f:
            f.write(json.dumps(data))
        return False
    return True


def scrape_name_pages(dir_names: Path, path_index: Path, cpus: int):
    """The main method for scraping SeqCode name pages."""

    # Read existing files from the names directory
    existing_files = list(dir_names.glob('name_*.json'))
    existing_ids = set()
    for file in existing_files:
        existing_ids.add(int(file.stem.split('name_')[-1]))

    # Read the index file and create the queue of IDs to scrape
    queue = list()
    n_ids_done = 0
    with path_index.open('r') as f:
        f.readline()
        for line in f:
            uid, name, url, uri = line.strip().split('\t')
            uid = int(uid)
            if uid in existing_ids:
                n_ids_done += 1
            else:
                queue.append((uid, url, dir_names))

    has_error = False
    with mp.Pool(cpus) as pool:
        # Use tqdm to show progress
        for is_error in tqdm(pool.imap_unordered(scrape_name_page_worker, queue), initial=n_ids_done,
                             total=len(queue) + n_ids_done):
            has_error = has_error or is_error
    return


def parse_name_pages(dir_names: Path, gtdb_taxa: Path, path_names: Path):
    """This method will parse the SeqCode name pages and save the data to a file."""

    # Read the content of all files
    name_files = list(dir_names.glob('name_*.json'))
    data = dict()
    for file_name in tqdm(name_files):
        with file_name.open('r') as f:
            page_data = json.load(f)
            uid = int(page_data['id'])
            data[uid] = page_data

    # Read the GTDB taxa file
    d_gtdb_taxon_to_id = dict()
    with gtdb_taxa.open('r') as f:
        for line in f.readlines():
            gtdb_id, taxon, in_db = line.strip().split('\t')
            d_gtdb_taxon_to_id[taxon] = (int(gtdb_id), int(in_db) == 1)

    # As a full taxonomy string is not provided, we must iterate down from the root to the leaf node.
    to_update = dict()
    n_miss = 0
    n_existing = 0
    for uid, page_data in data.items():
        page_rank = page_data['rank']
        page_name = page_data['name']

        if page_name.startswith('Candidatus '):
            page_name = page_name[11:]

        if page_rank in {'domain', 'phylum', 'class', 'order', 'family', 'genus', 'species'}:
            page_name_formatted = f"{page_rank[0]}__{page_name}"

            gtdb_match = d_gtdb_taxon_to_id.get(page_name_formatted)
            if gtdb_match:
                gtdb_id, in_db = gtdb_match
                if not in_db:
                    if page_name_formatted in to_update:
                        if page_data['name'].startswith('Candidatus '):
                            # Prefer non-Candidatus names
                            continue
                        raise Exception('??')
                    to_update[page_name_formatted] = (gtdb_id, page_data['uri'])
                else:
                    n_existing += 1
            else:
                n_miss += 1

    print(
        f'Done matching. Found {len(to_update):,} taxa to update, {n_existing:,} already in database, {n_miss:,} not found in GTDB tree table.')
    with path_names.open('w') as f:
        f.write('id\turl\n')
        for taxon, (gtdb_id, uri) in to_update.items():
            f.write(f'{gtdb_id}\t{uri}\n')

    print(f'Wrote parsed names to {path_names}')
    print('Import this into the "gtdb_tree_url_seqcode" table in the GTDB Common database.')
    print('Afterwards, run "CLUSTER gtdb_tree_url_seqcode"')

    return


def main(args):
    directory = Path(args.directory)
    gtdb_taxa = Path(args.gtdb_taxa)
    n_cpus = args.cpus

    # Create parameters
    dir_index = directory / 'index'
    dir_names = directory / 'names'
    path_index_parsed = directory / 'index_parsed.tsv'
    path_names_parsed = directory / 'names_parsed.tsv'

    # Create directories
    dir_index.mkdir(parents=True, exist_ok=True)
    dir_names.mkdir(parents=True, exist_ok=True)

    # Scrape the index pages
    if not path_index_parsed.exists():
        print('Scraping SeqCode index pages...')
        scrape_index_pages(dir_index, n_cpus)

        # Extract names from each of the index pages
        print('Extracting names from SeqCode index pages...')
        extract_names_from_pages(dir_index, path_index_parsed)
    else:
        print(f'Index parsed file {path_index_parsed} already exists. Skipping scraping.')

    # Read the names from the parsed file to scrape each name page
    if not path_names_parsed.exists():
        print('Scraping SeqCode name pages...')
        # scrape_name_pages(dir_names, path_index_parsed, n_cpus)

        # Extract names from the scraped name pages
        print('Parsing SeqCode name pages and matching to GTDB taxa...')
        parse_name_pages(dir_names, gtdb_taxa, path_names_parsed)
    else:
        print(f'Names parsed file {path_names_parsed} already exists. Skipping scraping.')

    print('Done.')
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='Directory to store temporary data.')
    parser.add_argument('gtdb_taxa', help='Path to the GTDB taxa file.')
    parser.add_argument('cpus', help='Number of CPUs to use in scraping.', type=int)
    main(parser.parse_args())

    """
    To generate the GTDB taxa file, use the following SQL command in the web database:
    
    select t.id, t.taxon, CASE WHEN s.id IS NULL THEN 0 else 1 END as in_db from gtdb_tree t
    LEFT JOIN gtdb_tree_url_seqcode s ON s.id = t.id
    where type in ('d', 'p', 'c', 'o', 'f', 'g', 's')
    """
