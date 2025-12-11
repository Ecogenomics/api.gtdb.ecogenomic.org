
if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import multiprocessing as mp
import requests

import json
from collections import defaultdict, Counter
from collections import deque

import sqlalchemy as sa
from sqlalchemy import insert
from tqdm import tqdm
import Levenshtein as lev
from api.db import GtdbSession, GtdbWebSession, GtdbCommonSession
# from api.db.models import DbGtdbTreeChildren, DbGtdbTree, GtdbCommonSeqCodeHtml, GtdbCommonLpsnHtml
# from api.db.models import MetadataTaxonomy, Genome
from api.util.collection import iter_batches

ROOT_ID = 0
JSON_PATH = '/tmp/genome_taxonomy_r214_count.json'


def read_json():
    # This is exported from GTDB release tk
    with open(JSON_PATH, 'r') as f:
        return json.load(f)


EXPECTED = {'name', 'type', 'children', 'countgen'}

EXPECTED_GENOME = {'name', 'type', 'rep', 'countgen', 'type_material'}

EXPECTED_SPECIES = {'name', 'type', 'children', 'countgen', 'type_material'}


def get_all_taxa_to_ids(data):
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
        rows_children.append(insert(DbGtdbTreeChildren).values(
            parent_id=parent_id,
            child_id=cur_id,
            order_id=order_id,
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
        rows_parent.append(insert(DbGtdbTree).values(
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

    return rows_parent, rows_children, d_extra_genomes


def insert_rows(rows_parent, rows_children):
    db = GtdbWebSession()

    parent_batches = list(iter_batches(rows_parent, 1000))
    for batch in tqdm(parent_batches):
        for stmt in batch:
            db.execute(stmt)
        db.commit()

    child_batches = list(iter_batches(rows_children, 1000))
    for batch in tqdm(child_batches):
        for stmt in batch:
            db.execute(stmt)
        db.commit()

    return


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


def get_extra_genomes(d_extra_genomes):
    gids_that_exist_in_tree = get_genome_ids_that_exist_in_db()

    db_web = GtdbWebSession()
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
        if full_gid not in gids_that_exist_in_tree:
            d_sp_to_gids[row.gtdb_species].add(full_gid)

    for parent_taxon, extra_genomes in tqdm(d_extra_genomes.items(), total=len(d_extra_genomes)):
        gids_to_add = d_sp_to_gids[parent_taxon]
        if len(gids_to_add) != extra_genomes and len(gids_to_add) != 0:
            raise Exception('??')

        # Get the parent id for this species
        query = sa.select([
            DbGtdbTree.id,
        ]).where(DbGtdbTree.taxon == parent_taxon)
        results = db_web.execute(query).fetchall()
        if len(results) != 1:
            raise ValueError('??')
        parent_id = results[0].id

        # Get the next ordering id
        query = sa.select([
            sa.func.max(DbGtdbTreeChildren.order_id),
        ]).where(DbGtdbTreeChildren.parent_id == parent_id)
        results = db_web.execute(query).fetchall()
        if len(results) != 1:
            raise ValueError('??')
        order_id = results[0][0] + 1

        # Get the next ID for this genome
        query = sa.select([
            sa.func.max(DbGtdbTree.id),
        ])
        results = db_web.execute(query).fetchall()
        if len(results) != 1:
            raise ValueError('??')
        next_id = results[0][0] + 1

        # Create the insert statements
        rows_main = list()
        rows_relation = list()

        for gid in sorted(gids_to_add):
            rows_main.append(insert(DbGtdbTree).values(
                id=next_id,
                taxon=gid,
                total=1,
                type='genome',
            ))
            rows_relation.append(insert(DbGtdbTreeChildren).values(
                parent_id=parent_id,
                child_id=next_id,
                order_id=order_id,
            ))
            next_id += 1
            order_id += 1

        insert_rows(rows_main, rows_relation)

    return




def update_with_bergeys():
    return


def update_with_ncbi():
    return


def check_seqcode_url_worker(job):
    gtdb_name, seqcode_id, seqcode_name= job
    seqcode_name_parsed = seqcode_name.replace(' ', '_')
    short_url = f'https://seqco.de/n:{seqcode_name_parsed}'
    long_url = f'https://disc-genomics.uibk.ac.at/seqcode/names/{seqcode_id}'
    r = requests.get(short_url)

    if r.ok:
        if r.url == long_url:
            return gtdb_name, short_url
        else:
            r_long = requests.get(long_url)
            if r_long.ok:
                if r_long.url == long_url:
                    return gtdb_name, long_url
                else:
                    raise ValueError(job)
            else:
                raise ValueError(job)
    else:
        raise ValueError(job)

def check_seqcode_url(queue):
    out = dict()

    with mp.Pool(processes=10) as pool:
        results = list(tqdm(pool.imap_unordered(check_seqcode_url_worker, queue), total=len(queue)))

    for result in results:
        out[result[0]] = result[1]
    return out

def get_from_seqcode_db():
    print(f'Getting all data from SeqCode table')
    db_common = GtdbCommonSession()

    # Get the domain ids
    query_d = sa.select([GtdbCommonSeqCodeHtml.id, GtdbCommonSeqCodeHtml.name, GtdbCommonSeqCodeHtml.rank,
                         GtdbCommonSeqCodeHtml.domain_id, GtdbCommonSeqCodeHtml.phylum_id,
                         GtdbCommonSeqCodeHtml.class_id, GtdbCommonSeqCodeHtml.order_id,
                         GtdbCommonSeqCodeHtml.family_id, GtdbCommonSeqCodeHtml.genus_id])
    results_d = db_common.execute(query_d).fetchall()
    print(f'Found {len(results_d):,} rows')
    out = defaultdict(set)
    out2 = dict()
    for result in results_d:
        out[result.rank].add(result.id)
        out2[result.id] = dict(result)

    return out, out2

def sanitise_seqcode_name(name):
    if 'Candidatus ' in name:
        name = name.replace('Candidatus ', '')
    if '(phylum)' in name:
        name = name.replace('(phylum)', '')
    if '(class)' in name:
        name = name.replace('(class)', '')
    if '(order)' in name:
        name = name.replace('(order)', '')
    if '(family)' in name:
        name = name.replace('(family)', '')
    if '(genus)' in name:
        name = name.replace('(genus)', '')
    if '(species)' in name:
        name = name.replace('(species)', '')
    return name.strip()

def update_with_seqcode(d_taxa_to_id, d_sp_to_higher_ranks):

    # Match the species first, then work the way up the tree
    d_rank_to_ids, d_id_to_row = get_from_seqcode_db()

    # Match all species where possible
    rows_not_matched = set()
    d_seqcode_id_to_db_id = dict()
    d_taxon_to_seqcode_id = dict()
    d_gtdb_taxon_to_vote = defaultdict(lambda: defaultdict(list))
    for cur_id in tqdm(sorted(d_rank_to_ids['species']), total=len(d_rank_to_ids['species'])):
        cur_row = d_id_to_row[cur_id]

        cur_name = cur_row['name']
        cur_name = sanitise_seqcode_name(cur_name)
        cur_name = f's__{cur_name}'

        cur_hit = d_taxa_to_id.get(cur_name)
        if cur_hit is None:
            rows_not_matched.add(cur_id)
        else:

            d_seqcode_id_to_db_id[cur_id] = cur_hit
            d_taxon_to_seqcode_id[cur_name] = cur_id

            higher_ranks = d_sp_to_higher_ranks[cur_name]


            # Go up the higher ranks and associate them, unless they are polyphyletic
            for rank, db_name in higher_ranks.items():
                if rank == 'gtdb_species':
                    continue

                rank = rank.split('_')[1]
                seqcode_rank = cur_row[f'{rank}_id']
                if seqcode_rank is None:
                    continue

                seqcode_rank_row = d_id_to_row[seqcode_rank]
                if seqcode_rank_row['name'] is None:
                    continue
                seqcode_row_name = sanitise_seqcode_name(seqcode_rank_row['name'])
                seqcode_row_name = f'{rank[0]}__{seqcode_row_name}'

                d_gtdb_taxon_to_vote[db_name][seqcode_row_name].append(seqcode_rank_row['id'])

    d_out_final = dict()
    for gtdb_taxon, d_seqcode_to_votes in d_gtdb_taxon_to_vote.items():

        # If any of them are a verbatim match, then use those
        seqcode_taxids = d_seqcode_to_votes.get(gtdb_taxon)
        if seqcode_taxids is not None:
            if len(set(seqcode_taxids)) == 1:
                d_out_final[gtdb_taxon] = seqcode_taxids[0]
                continue
            else:
                hits = Counter(seqcode_taxids).most_common()
                print(f'Using {hits[0][0]} for {gtdb_taxon} (other votes: {hits[1:]})')
                d_out_final[gtdb_taxon] = hits[0][0]
        else:
            # Valid name but poly group
            if gtdb_taxon[0] in {'d', 'p', 'c', 'o', 'f'} and gtdb_taxon[-2] == '_':
                continue
            else:
                # Take the most common
                sorted_votes = sorted(d_seqcode_to_votes.items(), key=lambda x: len(x[1]), reverse=True)
                most_common = sorted_votes[0]

                most_common_start = most_common[0][3]
                gtdb_start = gtdb_taxon[3]

                if most_common_start != gtdb_start:
                    print(f'Skipping: {most_common[0]} != {gtdb_taxon}')
                    continue

                ratio = lev.ratio(most_common[0], gtdb_taxon)
                if ratio > 0.83:
                    d_out_final[gtdb_taxon] = Counter(most_common[1]).most_common(1)[0][0]
                    continue

    # Find those with valid URLs
    queue = [(x[0], x[1], d_id_to_row[x[1]]['name']) for x in d_out_final.items()]
    d_seqcode_final = check_seqcode_url(queue)
    print(f'Found {len(d_seqcode_final):,} to update')

    db_web = GtdbWebSession()
    for gtdb_taxon, seqcode_url in d_seqcode_final.items():
        gtdb_tree_id = d_taxa_to_id[gtdb_taxon]
        stmt = sa.update(DbGtdbTree).where(DbGtdbTree.id == gtdb_tree_id).values(seqcode_url=seqcode_url)
        db_web.execute(stmt)
    db_web.commit()


    return d_out_final


def get_taxa_and_id_from_db():
    print('Getting taxa and id from db')
    db_web = GtdbWebSession()
    query = sa.select([
        DbGtdbTree.taxon,
        DbGtdbTree.id,
    ]).where(DbGtdbTree.type != 'genome').where(DbGtdbTree.type != 'root')
    results = db_web.execute(query).fetchall()
    out = dict()
    for result in tqdm(results):
        out[result.taxon] = result.id
    print(f'Found {len(out):,} taxa')
    return out

def get_species_higher_ranks():
    out = dict()
    db = GtdbSession()
    query = sa.select([
        MetadataTaxonomy.gtdb_domain,
        MetadataTaxonomy.gtdb_phylum,
        MetadataTaxonomy.gtdb_class,
        MetadataTaxonomy.gtdb_order,
        MetadataTaxonomy.gtdb_family,
        MetadataTaxonomy.gtdb_genus,
        MetadataTaxonomy.gtdb_species]
    ).where(MetadataTaxonomy.gtdb_species != 's__').distinct()
    results = db.execute(query).fetchall()
    for result in results:
        out[result.gtdb_species] = dict(result)
    return out


def update_db():
    data = read_json()

    # Generate the rows
    rows_parent, rows_children, d_extra_genomes = get_all_taxa_to_ids(data)
    # insert_rows(rows_parent, rows_children)

    get_extra_genomes(d_extra_genomes)

def update_external_links():
    d_taxa_to_id = get_taxa_and_id_from_db()
    # d_sp_to_higher_ranks = get_species_higher_ranks()

    # update_with_seqcode(d_taxa_to_id, d_sp_to_higher_ranks)
    update_with_lpsn(d_taxa_to_id)
    return

def update_with_lpsn(d_taxa_to_id):


    # Get the data from the LPSN table
    print('Getting rows from LPSN table')
    db = GtdbCommonSession()
    query = sa.select([
        GtdbCommonLpsnHtml.url,
        GtdbCommonLpsnHtml.name,
        GtdbCommonLpsnHtml.category,
        GtdbCommonLpsnHtml.proposed_as,
        GtdbCommonLpsnHtml.taxonomic_status
    ])
    results = db.execute(query).fetchall()
    print(f'Found {len(results):,} rows')

    d_lpsn_name_to_row = dict()
    for result in results:
        cur_url = result['url']
        cur_name = result['name']
        cur_category = cur_url.split('/')[-2]
        cur_proposed_as = result['proposed_as']
        cur_taxonomic_status = result['taxonomic_status']

        cur_name_parsed = cur_url.split('/')[-1].capitalize()
        cur_name_prefix = f'{cur_category.lower()[0]}__{cur_name_parsed}'

        if cur_name_prefix in d_taxa_to_id:
            if cur_name_prefix in d_lpsn_name_to_row:
                print('??')
            d_lpsn_name_to_row[cur_name_prefix] = cur_url

    db_web = GtdbWebSession()
    for taxon, url in tqdm(d_lpsn_name_to_row.items(), total=len(d_lpsn_name_to_row)):
        row_id = d_taxa_to_id[taxon]

        # Generate the update query
        stmt = sa.update(DbGtdbTree).where(DbGtdbTree.id == row_id).values(lpsn_url=url)
        db_web.execute(stmt)
        db_web.commit()


    return


def main():
    update_db()
    update_external_links()



    return


if __name__ == '__main__':
    main()
