from collections import defaultdict

PATH_AR53_SYNONYMS = '/tmp/synonyms.ar53_r232.tsv'
PATH_BAC120_SYNONYMS = '/tmp/synonyms.bac120_r232.tsv'
IMPORT_SCRIPT_PATH = '/tmp/gtdb_synonyms.sql'


def read_synonym_file(path):
    print(f'Reading file: {path}')
    out = defaultdict(set)
    n_skip = 0
    with open(path, 'r') as f:
        col_to_idx = {c: i for i, c in enumerate(f.readline().strip().split('\t'))}
        for line in f:
            cols = line.strip().split('\t')
            taxon = cols[col_to_idx['GTDB species']].strip()
            synonym = cols[col_to_idx['Synonym']].strip()

            # Skip placeholder strings
            if taxon == 's__' or synonym == 's__':
                n_skip += 1
                continue

            if len(taxon) < 4:
                print(f'{path} contains a taxon that is suspiciously short {taxon} at line: {line}')
                exit(1)
            if len(synonym) < 4:
                print(f'{path} contains a synonym that is suspiciously short {synonym} at line: {line}')
                exit(1)
            out[taxon].add(synonym)
    print(f'Found {len(out):,} synonyms, skipped {n_skip:,} taxa due to placeholder strings.')
    return out


def generate_export_sql(synonyms):
    sql = ['INSERT INTO gtdb_synonym (taxon, synonyms) VALUES ']

    for taxon, synonyms in sorted(synonyms.items()):
        sorted_synonyms = sorted(synonyms)
        sorted_synonyms_str = '", "'.join(sorted_synonyms)
        sorted_synonyms_str = '{"' + sorted_synonyms_str + '"}'

        sql.append(f"('{taxon}', '{sorted_synonyms_str}'), ")

    sql.append(';')

    print(f'Writing import script to {IMPORT_SCRIPT_PATH}')
    with open(IMPORT_SCRIPT_PATH, 'w') as f:
        f.write('\n'.join(sql))


def main():
    ar53_synonyms = read_synonym_file(PATH_AR53_SYNONYMS)
    bac120_synonyms = read_synonym_file(PATH_BAC120_SYNONYMS)

    taxa_intersect = set(ar53_synonyms.keys()).intersection(set(bac120_synonyms.keys()))
    if len(taxa_intersect) > 0:
        print(f'Found intersecting taxa between ar53 and bac120 set: {taxa_intersect}')
        exit(1)

    all_synonyms = {**ar53_synonyms, **bac120_synonyms}

    generate_export_sql(all_synonyms)

    print('Done.')

    return


if __name__ == '__main__':
    main()
