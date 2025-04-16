import os

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import json
from collections import defaultdict
from collections import deque

import sqlalchemy as sa
from tqdm import tqdm

from api.db import GtdbSession, GtdbWebSession
from api.db.models import DbGtdbTree, GtdbWebUrlBergeys, GtdbWebUrlSeqcode, GtdbWebUrlLpsn, GtdbWebUrlNcbi, \
    GtdbWebUrlSandPiper
from api.db.models import MetadataTaxonomy, Genome

# Configuration
JSON_PATH = '/private/tmp/release226/genome_taxonomy_r226_count.json'
OUT_DIR = '/tmp/release226_tree'

# Globals
EXPECTED = {'name', 'type', 'children', 'countgen'}
EXPECTED_GENOME = {'name', 'type', 'rep', 'countgen', 'type_material'}
EXPECTED_SPECIES = {'name', 'type', 'children', 'countgen', 'type_material'}


def parse_json_file():
    with open(JSON_PATH) as f:
        data = json.load(f)

    d_name_to_id = {
        'root': 0
    }
    d_id_to_name = {
        0: 'root'
    }

    rows_children = list()
    rows_parent = list()
    d_extra_genomes = dict()

    if data['type'] != 'root':
        raise ValueError(f'Expected type, got {data["type"]}')

    queue = deque([])

    for i, child in enumerate(data['children']):
        queue.append((0, child, i))

    while len(queue) > 0:
        parent_id, node, order_id = queue.pop()

        cur_name = node['name']
        cur_total = node['countgen']

        if 'extra_genomes' in node:
            d_extra_genomes[d_id_to_name[parent_id]] = node['extra_genomes']
            continue

        if node['type'] == 'genome':
            if len(set(node.keys() - EXPECTED_GENOME)) > 0:
                print('??')
        elif node['type'] == 's':
            if len(set(node.keys() - EXPECTED_SPECIES)) > 0:
                print('??')
        else:
            if set(node.keys()) != EXPECTED:
                print('??')

        if cur_name in d_name_to_id:
            raise ValueError(f'Name {cur_name} already exists')

        cur_id = len(d_name_to_id)
        d_name_to_id[cur_name] = cur_id
        d_id_to_name[cur_id] = cur_name

        # Create the child row mapping
        rows_children.append(dict(
            parent_id=parent_id,
            child_id=cur_id,
            order_id=order_id
        ))

        # Calculate the number of descendant children (ranks above genus _A are poly)
        if node['type'] in {'genome', 's'}:
            n_desc_children = None
        elif node['type'] == 'g':
            n_desc_children = len(node['children'])
        else:
            child_names = [x['name'] for x in node['children']]
            all_names = set()
            for child_name in child_names:
                if child_name[-2] == '_':
                    all_names.add(child_name[:-2])
                else:
                    all_names.add(child_name)
            n_desc_children = len(all_names)

        # Create the parent row
        rows_parent.append(dict(
            id=cur_id,
            taxon=cur_name,
            total=cur_total,
            type=node['type'],
            is_rep=node.get('rep') if node['type'] == 'genome' else None,
            type_material=node.get('type_material'),
            n_desc_children=n_desc_children,
        ))

        # Enqueue the children
        for i, child in enumerate(node.get('children', list())):
            queue.append((cur_id, child, i))

    rows_parent.append(dict(
        id=0,
        taxon='root',
        total=0,
        type='root',
        is_rep=None,
        type_material=None,
        n_desc_children=None
    ))

    return rows_parent, rows_children, d_extra_genomes


def get_genome_ids_that_exist_in_db():
    # Find those that already exist in the tree
    db = GtdbWebSession()
    query = sa.select([
        DbGtdbTree.taxon,
    ]).where(DbGtdbTree.type == 'genome')
    results = db.execute(query).fetchall()

    if len(results) == 0:
        raise ValueError('???')

    out = {x.taxon for x in results}
    return out


def convert_rows_children_to_dict(rows_children):
    # Group the rows
    out_tmp = defaultdict(list)
    for row in rows_children:
        out_tmp[row['parent_id']].append(dict(
            child_id=row['child_id'],
            order_id=row['order_id']
        ))

    # Sort them and drop the order_id value
    out = dict()
    for parent_id, lst_items in out_tmp.items():
        lst_sorted = sorted(lst_items, key=lambda x: x['order_id'])
        out[parent_id] = [x['child_id'] for x in lst_sorted]
    return out


def convert_rows_parent_to_dict(rows_parent):
    out2 = dict()
    out = dict()
    for row in rows_parent:
        cur_taxon = row['taxon']
        cur_id = row['id']
        assert cur_taxon not in out
        assert cur_id not in out
        out[cur_taxon] = row
        out2[cur_id] = row
    return out, out2


def get_genome_species():
    db_gtdb = GtdbSession()

    # Get all species that do not belong to those that exist in the tree
    query = sa.select([
        Genome.name,
        MetadataTaxonomy.gtdb_species,
    ]).join(MetadataTaxonomy, Genome.id == MetadataTaxonomy.id).where(MetadataTaxonomy.gtdb_species != 's__')
    results = db_gtdb.execute(query).fetchall()

    d_sp_to_gids = defaultdict(set)

    for row in results:
        if row.name.startswith('GCA_'):
            full_gid = f'GB_{row.name}'
        elif row.name.startswith('GCF_'):
            full_gid = f'RS_{row.name}'
        else:
            raise ValueError('F??')
        d_sp_to_gids[row.gtdb_species].add(full_gid)
    return d_sp_to_gids


def get_extra_genomes(rows_parent, rows_children, d_extra_genomes):
    # Convert the rows into a usable format
    d_parent_id_to_children = convert_rows_children_to_dict(rows_children)
    d_taxon_to_row, d_id_to_row = convert_rows_parent_to_dict(rows_parent)

    # Get the genomes in each species
    d_sp_to_gids = get_genome_species()

    # Go over each species to find those to be added
    for parent_taxon, n_extra_genomes in tqdm(d_extra_genomes.items()):
        gids_in_species = d_sp_to_gids[parent_taxon]
        parent_tree_id = d_taxon_to_row[parent_taxon]['id']
        tree_child_ids = d_parent_id_to_children[parent_tree_id]
        tree_child_names = {d_id_to_row[x]['taxon'] for x in tree_child_ids}
        assert len(tree_child_names) == len(tree_child_ids)
        gids_to_add = gids_in_species - tree_child_names
        assert len(gids_to_add) == n_extra_genomes

        for gid_to_add in sorted(gids_to_add):
            new_id = len(d_taxon_to_row) + 1
            assert gid_to_add not in d_taxon_to_row

            # Add the parent mapping
            d_taxon_to_row[gid_to_add] = dict(
                id=new_id,
                taxon=gid_to_add,
                total=1,
                type='genome',
                is_rep=False,
                type_material=None,
                n_desc_children=None
            )

            # Add the child mapping
            d_parent_id_to_children[parent_tree_id].append(new_id)

    # Convert them back to row format
    out_parent = list(d_taxon_to_row.values())
    out_children = list()
    for parent_id, lst_children in d_parent_id_to_children.items():
        for order_id, child_id in enumerate(lst_children):
            out_children.append(dict(
                parent_id=parent_id,
                child_id=child_id,
                order_id=order_id
            ))

    return out_parent, out_children


def get_previous_release_annotations():
    db = GtdbWebSession()
    query = (sa.select([
        DbGtdbTree.taxon.label('taxon'),
        GtdbWebUrlBergeys.url.label('bergeys_url'),
        GtdbWebUrlSeqcode.url.label('seqcode_url'),
        GtdbWebUrlLpsn.url.label('lpsn_url'),
        GtdbWebUrlNcbi.taxid.label('ncbi_taxid'),
        GtdbWebUrlSandPiper.url.label('sandpiper_url')
    ])
             .outerjoin(GtdbWebUrlBergeys, GtdbWebUrlBergeys.id == DbGtdbTree.id)
             .outerjoin(GtdbWebUrlSeqcode, GtdbWebUrlSeqcode.id == DbGtdbTree.id)
             .outerjoin(GtdbWebUrlLpsn, GtdbWebUrlLpsn.id == DbGtdbTree.id)
             .outerjoin(GtdbWebUrlNcbi, GtdbWebUrlNcbi.id == DbGtdbTree.id)
             .outerjoin(GtdbWebUrlSandPiper, GtdbWebUrlSandPiper.id == DbGtdbTree.id)
             )

    results = db.execute(query).fetchall()

    out = defaultdict(dict)
    for row in results:
        if row.bergeys_url is not None:
            out[row.taxon]['bergeys_url'] = row.bergeys_url
        if row.seqcode_url is not None:
            out[row.taxon]['seqcode_url'] = row.seqcode_url
        if row.lpsn_url is not None:
            out[row.taxon]['lpsn_url'] = row.lpsn_url
        if row.ncbi_taxid is not None:
            out[row.taxon]['ncbi_taxid'] = row.ncbi_taxid
        if row.sandpiper_url is not None:
            out[row.taxon]['sandpiper_url'] = row.sandpiper_url
    return out


def create_import_tsv(rows_parent, rows_children, d_taxon_to_annotations):
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(OUT_DIR, 'gtdb_tree.tsv'), 'w') as f:
        f.write('\t'.join((
            'id', 'taxon', 'total', 'type', 'is_rep', 'type_material',
            'n_desc_children'
        )) + '\n')
        for row in rows_parent:
            cur_row = [
                row['id'],
                row['taxon'],
                row['total'],
                row['type'],
                row['is_rep'],
                row['type_material'],
                row['n_desc_children'],
            ]
            cur_row = list(map(lambda x: x if x is not None else '', cur_row))
            cur_row = list(map(str, cur_row))
            f.write('\t'.join(cur_row) + '\n')

    with open(os.path.join(OUT_DIR, 'bergeys.tsv'), 'w') as f:
        f.write('\t'.join(('id', 'url')) + '\n')
        for row in rows_parent:
            cur_anno = d_taxon_to_annotations.get(row['taxon'], dict())
            cur_anno = cur_anno.get('bergeys_url')
            if cur_anno is not None:
                cur_id = row['id']
                f.write(f'{cur_id}\t{cur_anno}\n')

    with open(os.path.join(OUT_DIR, 'seqcode.tsv'), 'w') as f:
        f.write('\t'.join(('id', 'url')) + '\n')
        for row in rows_parent:
            cur_anno = d_taxon_to_annotations.get(row['taxon'], dict())
            cur_anno = cur_anno.get('seqcode_url')
            if cur_anno is not None:
                cur_id = row['id']
                f.write(f'{cur_id}\t{cur_anno}\n')

    with open(os.path.join(OUT_DIR, 'lpsn.tsv'), 'w') as f:
        f.write('\t'.join(('id', 'url')) + '\n')
        for row in rows_parent:
            cur_anno = d_taxon_to_annotations.get(row['taxon'], dict())
            cur_anno = cur_anno.get('lpsn_url')
            if cur_anno is not None:
                cur_id = row['id']
                f.write(f'{cur_id}\t{cur_anno}\n')

    with open(os.path.join(OUT_DIR, 'ncbi.tsv'), 'w') as f:
        f.write('\t'.join(('id', 'taxid')) + '\n')
        for row in rows_parent:
            cur_anno = d_taxon_to_annotations.get(row['taxon'], dict())
            cur_anno = cur_anno.get('ncbi_taxid')
            if cur_anno is not None:
                cur_id = row['id']
                f.write(f'{cur_id}\t{cur_anno}\n')

    with open(os.path.join(OUT_DIR, 'sandpiper.tsv'), 'w') as f:
        f.write('\t'.join(('id', 'url')) + '\n')
        for row in rows_parent:
            cur_anno = d_taxon_to_annotations.get(row['taxon'], dict())
            cur_anno = cur_anno.get('sandpiper_url')
            if cur_anno is not None:
                cur_id = row['id']
                f.write(f'{cur_id}\t{cur_anno}\n')

    with open(os.path.join(OUT_DIR, 'gtdb_tree_children.tsv'), 'w') as f:
        f.write('\t'.join(('parent_id', 'child_id', 'order_id')) + '\n')
        for row in rows_children:
            cur_row = [
                row['parent_id'],
                row['child_id'],
                row['order_id']
            ]
            cur_row = list(map(str, cur_row))
            f.write('\t'.join(cur_row) + '\n')
    return


def main():
    print('Getting NCBI/Bergeys/SeqCode annotations from previous release')
    d_taxon_to_annotations = get_previous_release_annotations()

    print('Converting the JSON file to tuples')
    rows_parent, rows_children, d_extra_genomes = parse_json_file()

    print('Getting the "extra genomes" for each species.')
    rows_parent, rows_children = get_extra_genomes(rows_parent, rows_children, d_extra_genomes)

    print('Exporting to tsv')
    create_import_tsv(rows_parent, rows_children, d_taxon_to_annotations)
    return


if __name__ == '__main__':
    main()
