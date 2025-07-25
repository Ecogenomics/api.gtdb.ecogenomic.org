if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import hashlib
import multiprocessing as mp
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict
from urllib.request import urlopen, urlretrieve

import sqlalchemy as sa
from tqdm import tqdm

from api.db import GtdbFastaniSession
from api.db.models import GtdbFastaniGenome

CPUS = 5

DEBUG = False

CHUNK_SIZE_DOWNLOAD = 100
if DEBUG:
    CHUNK_SIZE_DOWNLOAD = 2

TARGET_DIR = '/mnt/ncbi-genomes/ncbi'
if DEBUG:
    TARGET_DIR = '/tmp/genomes'

NCBI_ROOT = 'https://ftp.ncbi.nlm.nih.gov/genomes'
REFSEQ_ARC = f'{NCBI_ROOT}/refseq/archaea/assembly_summary.txt'
REFSEQ_BAC = f'{NCBI_ROOT}/refseq/bacteria/assembly_summary.txt'
GENBANK_ARC = f'{NCBI_ROOT}/genbank/archaea/assembly_summary.txt'
GENBANK_BAC = f'{NCBI_ROOT}/genbank/bacteria/assembly_summary.txt'

R_ARC = os.path.join(TARGET_DIR, 'refseq_archaea.txt')
R_BAC = os.path.join(TARGET_DIR, 'refseq_bacteria.txt')
G_ARC = os.path.join(TARGET_DIR, 'genbank_archaea.txt')
G_BAC = os.path.join(TARGET_DIR, 'genbank_bacteria.txt')

URLLIB_TIMEOUT = 60 * 3


def log(msg):
    out = f'{datetime.now()}: {msg}'
    print(out)


class TqdmUpTo(tqdm):
    """Provides `update_to(n)` which counts up to `n`"""

    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (bytes) [default: 1].
        tsize  : int, optional
            Total size (bytes) of the download [default: None].
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)  # will also set self.n = b * bsize


def download_file_with_progress(url, filename):
    """Downloads a file from a URL with a tqdm progress bar."""
    with TqdmUpTo(unit='B', unit_scale=True, miniters=1, desc=filename) as t:
        urlretrieve(url, filename, reporthook=t.update_to)


def download_assembly_file(url, target):
    """Downloads the NCBI assembly summary file."""
    temp_file = f'{target}.dl'
    download_file_with_progress(url, temp_file)
    shutil.move(temp_file, target)


def download_file_worker(job):
    """Downloads a FNA file."""
    accession, root_url = job
    try:
        target_dir = os.path.join(TARGET_DIR, accession[0:3], accession[4:7],
                                  accession[7:10], accession[10:13])
        os.makedirs(target_dir, exist_ok=True)

        # set paths
        target_path = os.path.join(target_dir, f'{accession}.fna.gz')
        target_path_tmp = f'{target_path}.tmp'

        checksum_url = os.path.join(root_url, 'md5checksums.txt')

        target_url_basename = f'{os.path.basename(root_url)}_genomic.fna.gz'
        fna_url = os.path.join(root_url, target_url_basename)

        # Stop processing if it's already been downloaded
        if os.path.isfile(target_path):
            return accession, None, root_url, False, 'Existing file found'

        # Download the FNA
        start_time = time.time()
        with open(target_path_tmp, 'wb') as fw:
            with urlopen(fna_url, timeout=URLLIB_TIMEOUT) as f:
                fw.write(f.read())

        # Compute the checksum
        with open(target_path_tmp, 'rb') as f:
            computed_md5 = hashlib.md5(f.read()).hexdigest()

        # Get the checksums
        expected_md5 = None
        with urlopen(checksum_url, timeout=URLLIB_TIMEOUT) as f:
            for line in f.readlines():
                md5, basename = line.decode('utf-8').strip().split()
                basename = basename.lstrip('./')

                if basename == target_url_basename:
                    expected_md5 = md5

        # Move the file if the checksum is valid
        if computed_md5 == expected_md5:
            shutil.move(target_path_tmp, target_path)
            duration = round(time.time() - start_time, 2)
            return accession, expected_md5, root_url, True, 'OK'
            # log(f'> downloaded {accession} after {duration:,} seconds')
        else:
            return accession, expected_md5, root_url, False, 'MD5 mismatch'
    except Exception as e:
        return accession, None, root_url, False, str(e)


def download_assembly_files(ignore_existing=False):
    """Downloads all assembly files into the target directory."""
    os.makedirs(TARGET_DIR, exist_ok=True)
    targets = ((REFSEQ_ARC, R_ARC), (REFSEQ_BAC, R_BAC), (GENBANK_ARC, G_ARC), (GENBANK_BAC, G_BAC))
    for url, target in targets:
        if ignore_existing and os.path.exists(target):
            log(f'WARNING: Skipping {target} as ignore_existing=True')
        else:
            download_assembly_file(url, target)


def read_genomes_table():
    """This will read what genomes are in the GTDB FastANI database."""
    db = GtdbFastaniSession()
    try:
        query = sa.select([GtdbFastaniGenome.name, GtdbFastaniGenome.fna_gz_md5])
        results = db.execute(query).fetchall()
        out = defaultdict(dict)
        for row in results:
            out[row.name] = row.fna_gz_md5
        return out
    finally:
        db.close()


def read_assembly_files() -> Dict[str, str]:
    files = (R_ARC, R_BAC, G_ARC, G_BAC)
    out = dict()
    for assembly_path in files:
        n_found = 0
        with open(assembly_path) as f:
            for line in f.readlines():
                if line.startswith('#'):
                    continue
                cols = line.split('\t')
                accession = cols[0]
                ftp_path = cols[19]
                out[accession] = ftp_path
                n_found += 1
        log(f'    - Found {n_found:,} genomes in {assembly_path}')
    return out


def insert_genomes_into_db(rows):
    db = GtdbFastaniSession()
    try:
        for row in rows:
            db.execute(sa.insert(GtdbFastaniGenome).values({
                'name': row[0],
                'fna_gz_md5': row[1],
                'assembly_url': row[2],
            }))
        db.commit()
    finally:
        db.close()


def download_genomes_mp(queue):
    results = list()
    with tqdm(total=len(queue), miniters=1) as pbar:
        for i in range(0, len(queue), CHUNK_SIZE_DOWNLOAD):
            queue_chunk = queue[i:i + CHUNK_SIZE_DOWNLOAD]
            with mp.Pool(processes=CPUS) as pool:
                for result in pool.imap_unordered(download_file_worker, queue_chunk):
                    results.append(result)
                    pbar.update()

            # log('Updating database with downloaded genomes...')
            valid_results = [{
                'accession': r[0],
                'fna_gz_md5': r[1],
                'assembly_url': r[2],
            } for r in results if r[3]]
            # print(valid_results)
            insert_genomes_into_db(valid_results)

    error_results = [r for r in results if not r[3]]
    if len(error_results) > 0:
        temp_file_path = '/tmp/failed_genomes.txt'
        log(f'WARNING: {len(error_results):,} genomes failed to download, errors will be written to {temp_file_path}')
        with open(temp_file_path, 'w') as f:
            f.write('accession\tmd5\tftp_path\terror_message\n')
            for r in error_results:
                f.write(f'{r[0]}\t{r[1]}\t{r[2]}\t{r[4]}\n')

    return results


def main():
    if DEBUG:
        log("WARNING: USING DEBUGGING MODE!")

    log('Begin updating the FastANI database...')

    log('Downloading the NCBI assembly summary files.')
    download_assembly_files(ignore_existing=DEBUG)

    log('Reading genomes from the assembly summary files.')
    assembly_genomes = read_assembly_files()
    log(f'Found {len(assembly_genomes):,} genomes in the assembly summary files.')

    log('Reading existing genomes from GTDB FastANI database.')
    if DEBUG:
        existing_genomes = dict()
    else:
        existing_genomes = read_genomes_table()
    log(f'Found {len(existing_genomes):,} genomes in the GTDB FastANI database.')

    genomes_missing = set(assembly_genomes.keys()) - set(existing_genomes.keys())
    log(f'Found {len(genomes_missing):,} genomes to download.')

    if len(genomes_missing) == 0:
        log('No genomes to download, done!')
        sys.exit(0)

    queue = [(k, assembly_genomes[k]) for k in genomes_missing]

    if DEBUG:
        queue = queue[0:11]
    download_genomes_mp(queue)

    log('Done.')
    return


if __name__ == '__main__':
    main()
