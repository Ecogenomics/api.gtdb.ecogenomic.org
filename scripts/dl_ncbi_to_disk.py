"""
This script synchronises the NCBI website with the local disk and performs
checksum validation.

This is used by FastANI workers.
"""

import hashlib
import multiprocessing as mp
import os
import shutil
import time
from datetime import datetime
from typing import Dict
from urllib.request import urlopen

from tqdm import tqdm

CPUS = 5

MAX_QUEUE_SIZE = 100

TARGET_DIR = '/mnt/ncbi_genomes/ncbi'
# TARGET_DIR = '/tmp/genomes'

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


def download_assembly_file(url, target):
    """Downloads the NCBI assembly summary file."""
    log(f'Downloading to: {target}')
    temp_file = f'{target}.dl'
    with open(temp_file, 'w') as fw:
        with urlopen(url, timeout=URLLIB_TIMEOUT) as f:
            for line in f.read().decode('utf-8').splitlines():
                if line.startswith('#'):
                    continue
                cols = line.split('\t')
                accession = cols[0]
                ftp_path = cols[19]
                fw.write(f'{accession}\t{ftp_path}\n')
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
            # log(f'> skipping {accession}')
            return

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
            # log(f'> downloaded {accession} after {duration:,} seconds')
        else:
            raise ValueError(f'md5 mismatch, expected "{expected_md5}" but '
                             f'got "{computed_md5}"')
    except Exception as e:
        log(f'Exception downloading {accession}: {e}')
    return True


def download_assembly_files(ignore_existing=True):
    """Downloads all assembly files into the target directory."""
    os.makedirs(TARGET_DIR, exist_ok=True)
    for url, target in [(REFSEQ_ARC, R_ARC), (REFSEQ_BAC, R_BAC),
                        (GENBANK_ARC, G_ARC), (GENBANK_BAC, G_BAC)]:
        if not os.path.exists(target) or not ignore_existing:
            download_assembly_file(url, target)


def read_assembly_file(assembly_path) -> Dict[str, str]:
    out = dict()
    with open(assembly_path) as f:
        for line in f.readlines():
            accession, ftp_path = line.strip().split('\t')
            out[accession] = ftp_path
    return out


def download_genomes_mp():
    for assembly_path in [R_ARC, R_BAC, G_ARC, G_BAC]:
        log(f'Processing {assembly_path}')
        queue = [(a, f) for a, f in read_assembly_file(assembly_path).items()]
        log(f'Processing {len(queue):,} items')

        with tqdm(total=len(queue)) as pbar:
            for i in range(0, len(queue), MAX_QUEUE_SIZE):
                queue_chunk = queue[i:i + MAX_QUEUE_SIZE]
                with mp.Pool(processes=CPUS) as pool:
                    for _ in list(pool.imap_unordered(download_file_worker,
                                                      queue_chunk)):
                        pbar.update()


def log(msg):
    out = f'{datetime.now()}: {msg}'
    print(out)


def main():
    download_assembly_files(ignore_existing=True)
    download_genomes_mp()

    log('Done.')


if __name__ == '__main__':
    main()
