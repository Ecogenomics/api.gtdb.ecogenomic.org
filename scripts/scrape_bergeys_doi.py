if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()


from api.db import GtdbWebSession
from api.db.models import DbGtdbTree


import os
import re
from collections import defaultdict
from typing import Dict, Tuple
import sqlalchemy as sa
from bs4 import BeautifulSoup
from tqdm import tqdm

"""
Requirements:

1. Navigate to the website https://onlinelibrary.wiley.com/browse/book/10.1002/9781118960608/toc

2. Run the following Javascript to expand all elements:

const classes = document.getElementsByClassName("accordion__control");

for (let i = 0; i < classes.length; i++) {
    const curClass = classes[i];
    if (curClass.ariaExpanded !== 'true') {
        curClass.click();
    }
}

// Save the page as 1.html (complete, do not do HTML only)

// Get the next pages (if needed, 4 in total, where title is 2, 3, 4).

const links = document.getElementsByTagName("a");

for (let i = 0; i < links.length; i++) {
    const curLink = links[i];
    if (curLink.title === "4") {
        curLink.click();
    }
}

Oceanicella

"""

HTML_PATHS = [
    '/Users/aaron/Desktop/bergeys/bergeys_1.html',
    '/Users/aaron/Desktop/bergeys/bergeys_2.html',
    '/Users/aaron/Desktop/bergeys/bergeys_3.html',
    '/Users/aaron/Desktop/bergeys/bergeys_4.html'
]

RE_HITS = re.compile(
    r'<h2 class="meta__title meta__title__margin"><span class="hlFld-Title"><a href="(.+)" class="publication_title visitable">(.+)<\/a><\/span><\/h2>')

path_gtdb_tree = '/Users/aaron/Desktop/bergeys/gtdb_tree.tsv'

PATH_CACHE = '/Users/aaron/Desktop/bergeys/cache.tsv'

PATH_R207_BAC = '/Users/aaron/Desktop/bergeys/bac120_taxonomy_r207.tsv'
PATH_R207_ARC = '/Users/aaron/Desktop/bergeys/ar53_taxonomy_r207.tsv'

def parse_html(path):
    print(f'Processing: {path}')
    with open(path) as f:
        html = f.read()
    html = html.replace('\n', '')
    soup = BeautifulSoup(html, 'html.parser')

    tree_titles = list(soup.find_all(class_='accordion__control--text'))

    links = list(soup.find_all(class_='item__body'))

    del soup

    # Get the heading names for each depth
    d_heading_level_to_name = dict()
    for item in tqdm(tree_titles):
        item_title = item.text.strip()
        item_id = item.parent.attrs['aria-controls']
        assert (item_id.startswith('heading-level'))
        d_heading_level_to_name[item_id] = item_title

    # Get the links
    link_results = list()
    for link in tqdm(links):

        titles = link.find_all(class_='visitable')
        assert (len(titles) == 1)
        title = titles[0]

        title_str = title.text.strip()
        title_url = title.attrs['href']
        title_parents = list()

        cur_node = link
        while True:
            if cur_node.attrs.get('id', '').startswith('heading-level'):
                title_parents.append(cur_node.attrs['id'])

            if cur_node.attrs.get('class', []) == ['accordion']:
                break

            cur_node = cur_node.parent

        title_parents = [d_heading_level_to_name[x] for x in reversed(title_parents)]

        link_results.append((
            title_str,
            title_url,
            tuple(title_parents),
        ))

    return set(link_results)


def read_gtdb_tree_table() -> Dict[str, Dict[str, Tuple[int, str]]]:
    # out = defaultdict(lambda: dict())
    # with open(path_gtdb_tree, 'r') as f:
    #     for line in f.readlines():
    #         cols = line.strip().split('\t')
    #         taxon_no_prefix = cols[1][3:]
    #         taxon_prefix = cols[1][0]
    #         out[taxon_no_prefix][taxon_prefix] = (int(cols[0]), cols[1])
    #         # if taxon_no_prefix in out:
    #         #     print('???')
    #         # out[taxon_no_prefix] = (int(cols[0]), cols[1])

    """This is an export of the GTDB tree table from the GTDB website."""
    db = GtdbWebSession()
    try:
        query = sa.select([DbGtdbTree.id, DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome').where( DbGtdbTree.taxon != 'root')
        results = db.execute(query).fetchall()

        out = defaultdict(dict)
        for row in results:
            taxon_no_prefix = row.taxon[3:]
            taxon_prefix = row.taxon[0]
            out[taxon_no_prefix][taxon_prefix] = (row.id, row.taxon)
            out[row.taxon] = row.id
        return out
    finally:
        db.close()


def read_taxonomy_files():
    out = dict()
    for path in (PATH_R207_ARC, PATH_R207_BAC):
        with open(path, 'r') as f:
            for line in f.readlines():
                _, tax = line.strip().split('\t')
                tax = tax.split(';')
                for i in range(len(tax)):
                    out[tax[i][3:]] = [x[3:] for x in tax[:i]]
    return out


def main():
    # Parse the output from the GTDB tree table

    print('Reading taxonomy files')
    d_taxon_to_parents = read_taxonomy_files()

    print('Loading data from the GTDB tree database table')
    gtdb_tree = read_gtdb_tree_table()

    # Read the manually extracted files from the Bergeys website
    if not os.path.isfile(PATH_CACHE):
        print('Loading data from the downloaded Bergeys HTML file')
        all_hits = set()
        for path in HTML_PATHS:
            hits = parse_html(path)
            all_hits.update(hits)
        with open(PATH_CACHE, 'w') as f:
            for title, url, parents in all_hits:
                f.write(f'{title}\t{url}\t{"|".join(parents)}\n')
    else:
        all_hits = set()
        with open(PATH_CACHE) as f:
            for line in f.readlines():
                title, url, parents = line.strip().split('\t')
                parents = parents.split('|')
                all_hits.add((title, url, tuple(parents)))

    # Try and match the hits
    rows = list()
    no_match = set()
    multi_doi = set()
    matches = dict()
    duplicate = list()
    duplicate_seen = set()
    for title, url, parents in all_hits:

        if title.startswith('“') or title.startswith('"'):
            title = title[1:].strip()
        if title.endswith('”') or title.endswith('"'):
            title = title[:-1].strip()

        if title.endswith(' fam. nov.'):
            title = title[:-10]
        if title.endswith(' ord. nov'):
            title = title[:-9]
        if title.endswith(' phy. nov.'):
            title = title[:-10]
        if title.endswith(' class. nov.'):
            title = title[:-12]
        if title.endswith(' gen. nov.'):
            title = title[:-10]
        if title.endswith(' ord. nov.'):
            title = title[:-10]
        if title.endswith(' phyl. nov.'):
            title = title[:-11]
        if title.endswith(' fam. nov'):
            title = title[:-9]
        if title.endswith(' gen. nov'):
            title = title[:-9]
        if title.endswith(' class nov.'):
            title = title[:-11]
        if title.endswith('fam. nov.'):
            title = title[:-9]
        if title.startswith('Form- '):
            title = title[6:]
        if title.startswith('Form-'):
            title = title[5:]

        if title.startswith('Candidatus '):
            title = title[11:]
        if title.startswith('Candidatus'):
            title = title[10:]

        tree_parents = d_taxon_to_parents.get(title)
        table_hit = gtdb_tree.get(title)

        if table_hit:
            if len(table_hit) == 1:
                table_id = list(table_hit.values())[0][0]

                if title in matches or title in duplicate_seen:
                    duplicate.append(f'{title}\t{url}\t{"|".join(parents)}')
                    if title in matches:
                        del matches[title]
                    duplicate_seen.add(title)

                else:
                    rows.append((table_id, url))
                    matches[title] = (table_id, parents, url)

            else:
                print('?')

        else:
            if tree_parents is not None:
                print('?')
            else:
                no_match.add(f'{title}\t{url}\t{"|".join(parents)}')


    with open('/tmp/cmds_to_run.txt', 'w') as f:
        for row_id, _, url in matches.values():
            f.write(f"UPDATE gtdb_tree SET bergeys_url='{url}' WHERE id={row_id};\n")

    with open('/tmp/no_mapping.txt', 'w') as f:
        f.write('title\turl\tparents\n')
        f.write('\n'.join(sorted(no_match)))

    with open('/tmp/duplicates.txt', 'w') as f:
        f.write(f'title\turl\tparents\n')
        f.write('\n'.join(sorted(duplicate)))

    print(len(no_match))
    print(f'No matches: {len(no_match):,}')
    print(f'Matches: {len(matches):,}')
    print(f'Duplicates: {len(duplicate):,}')

    return


if __name__ == '__main__':
    main()
