import os
import requests
import re

from tqdm import tqdm
import multiprocessing as mp


PATH_SAVE_PAGES = '/tmp/seq_code'

path_gtdb_tree = '/tmp/gtdb_tree.tsv'


RE_TAXON = re.compile(r'<h1>(.+)<\/h1>')
RE_RANK_SECTION = re.compile(r'<dl name="nomenclature" class="main-section name-details">(.+?)</dl>')
RE_RANK = re.compile(r'Rank<\/dt>\s*<dd>\s*(.+?)\s*<\/dd>')

RE_CLASSIFICATION_SECTION = re.compile(r'<dl name="taxonomy" class="main-section name-details">(.+?)</dl>')
RE_CLASSIFICATION = re.compile(r'')


def get_taxon_from_html(html):
    taxa = RE_TAXON.findall(html)
    if len(taxa) != 1:
        raise Exception('Cannot find')
    return taxa[0]

def get_rank_from_html(html):
    rank_sections = RE_RANK_SECTION.findall(html)
    if len(rank_sections) != 1:
        raise Exception('?')
    rank_section = rank_sections[0]

    rank_hits = RE_RANK.findall(rank_section)

    if len(rank_hits) != 1:
        raise Exception('?')

    return rank_hits[0].strip()

# def get_classification_from_html(html):
#     sections = RE_CLASSIFICATION_SECTION.findall(html)
#     if len(sections) != 1:
#         raise Exception('?')
#     section = sections[0]
#
#     rank_hits = RE_RANK.findall(section)
#
#     if len(rank_hits) != 1:
#         raise Exception('?')
#
#     return rank_hits[0].strip().findall(html)
#     if len(rank_sections) != 1:
#         raise Exception('?')
#     rank_section = rank_sections[0]
#
#     rank_hits = RE_RANK.findall(rank_section)
#
#     if len(rank_hits) != 1:
#         raise Exception('?')
#
#     return rank_hits[0].strip()
#
#     return

def read_gtdb_tree_table():
    out = dict()
    with open(path_gtdb_tree, 'r') as f:
        for line in f.readlines():
            cols = line.strip().split('\t')
            taxon = cols[1]
            out[taxon] = int(cols[0])
    return out


def parse_page(page_id):

    url = f'https://disc-genomics.uibk.ac.at/seqcode/names/{page_id}'

    r = requests.get(url)


    if r.status_code != 200:
        if r.status_code == 404:
            return page_id, None, None
        print(f'Failed to get {url}')
        return page_id, None, None

    html = r.text
    html = html.replace('\n', '')

    if 'User cannot access name' in html:
        return page_id, None, None

    taxon = get_taxon_from_html(html)
    rank = get_rank_from_html(html)
    # classification = get_classification_from_html(html)

    if taxon.startswith('<i>Candidatus</i>'):
        taxon = taxon[len('<i>Candidatus</i>')+1:]

    return page_id, taxon, rank



def main():

    os.makedirs(PATH_SAVE_PAGES, exist_ok=True)

    gtdb_tree = read_gtdb_tree_table()

    queue = list(range(1, 23819))
    # queue = list(range(1, 200))
    with mp.Pool(processes=20) as pool:
        results = list(tqdm(pool.imap_unordered(parse_page, queue), total=len(queue), smoothing=0.01))


    with open('/tmp/code_to_run.txt', 'w') as f_sql, open('/tmp/no_results.txt', 'w') as f_no:

        for page_id, taxon, rank in results:
            if taxon is None and rank is None:
                continue

            if rank == 'Species':
                taxon_prefixed = f's__{taxon}'
            elif rank == 'Genus':
                taxon_prefixed = f'g__{taxon}'
            elif rank == 'Family':
                taxon_prefixed = f'f__{taxon}'
            elif rank == 'Order':
                taxon_prefixed = f'o__{taxon}'
            elif rank == 'Class':
                taxon_prefixed = f'c__{taxon}'
            elif rank == 'Phylum':
                taxon_prefixed = f'p__{taxon}'
            elif rank == 'Domain':
                taxon_prefixed = f'd__{taxon}'
            else:
                raise Exception('?')

            gtdb_tree_id = gtdb_tree.get(taxon_prefixed)
            if gtdb_tree_id is None:
                # print(f'Cannot find {taxon_prefixed}')
                f_no.write(f'{page_id}\t{taxon}\t{rank}\t{taxon_prefixed}\n')
                continue

            else:
                url = f'https://disc-genomics.uibk.ac.at/seqcode/names/{page_id}'
                f_sql.write(f"UPDATE gtdb_tree SET seqcode_url='{url}' WHERE id={gtdb_tree_id};\n")

    return


if __name__ == '__main__':
    main()
