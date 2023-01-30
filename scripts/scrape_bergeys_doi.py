import os
import re
from collections import defaultdict

HTML_DIR = '/tmp/bergeys'

RE_HITS = re.compile(
    r'<h2 class="meta__title meta__title__margin"><span class="hlFld-Title"><a href="(.+)" class="publication_title visitable">(.+)<\/a><\/span><\/h2>')

path_gtdb_tree = '/tmp/gtdb_tree.tsv'


def parse_html(path):
    with open(path) as f:
        html = f.read()

    hits = RE_HITS.findall(html)
    print(f'Found {len(hits)} hits in {path}')
    return hits


def read_gtdb_tree_table():
    out = dict()
    with open(path_gtdb_tree, 'r') as f:
        for line in f.readlines():
            cols = line.strip().split('\t')
            taxon_no_prefix = cols[1][3:]
            if taxon_no_prefix in out:
                print('???')
            out[taxon_no_prefix] = (int(cols[0]), cols[1])
    return out


def main():
    gtdb_tree = read_gtdb_tree_table()


    all_hits = list()

    for filename in os.listdir(HTML_DIR):
        path = os.path.join(HTML_DIR, filename)

        all_hits.extend(parse_html(path))

    d_hits = defaultdict(set)
    for doi, title in all_hits:
        doi = f'https://onlinelibrary.wiley.com{doi}'
        d_hits[title].add(doi)

    # Try and match the hits
    rows = list()
    no_match = set()
    multi_doi = set()
    matches = set()
    for title, dois in d_hits.items():
        title_old = title


        if title.startswith('<i>') and title.endswith('</i>'):
            print()

        if title.endswith('.'):
            title = title[:-1]

        if title.endswith('nov'):
            if title.endswith('phy. nov'):
                title = title[:-9]
            elif title.endswith('phyl. nov'):
                title = title[:-10]
            elif title.endswith('class. nov'):
                title = title[:-11]
            elif title.endswith('class nov'):
                title = title[:-10]
            elif title.endswith('ord. nov'):
                title = title[:-9]
            elif title.endswith('fam. nov'):
                title = title[:-9]
            elif title.endswith('gen. nov'):
                title = title[:-9]
            else:
                print(f'Unknown suffix {title}')

            if title in d_hits:
                print(f'Already existing: {title} (from {title_old})')
                continue
            else:
                pass


        hit = gtdb_tree.get(title)
        if hit:
            if len(dois) > 1:
                multi_doi.add(title)
            else:
                rows.append((hit[0], list(dois)[0]))
                matches.add(title)
        else:
            no_match.add(title)

    with open('/tmp/cmds_to_run.txt', 'w') as f:
        for row_id, url in sorted(rows):
            f.write(f"UPDATE gtdb_tree SET bergeys_url='{url}' WHERE id={row_id};\n")

    with open('/tmp/no_mapping.txt', 'w') as f:
        f.write('\n'.join(sorted(no_match)))

    print(len(no_match))
    print(f'No matches: {len(no_match):,}')
    print(f'Matchess: {len(matches):,}')
    print(f'Total: {len(d_hits):,}')

    return


if __name__ == '__main__':
    main()
