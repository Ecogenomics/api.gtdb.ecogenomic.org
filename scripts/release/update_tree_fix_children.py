if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
from collections import defaultdict

import sqlalchemy as sa

from api.db import GtdbWebSession
# from api.db.models import DbGtdbTreeChildren, DbGtdbTree


def read_tree_rows():
    db = GtdbWebSession()
    try:
        query = sa.text("""
            select id, taxon, type, n_desc_children
            from gtdb_tree
            where type in ('d', 'p', 'c', 'o', 'f', 'g', 's');
        """)
        results = db.execute(query).fetchall()
        d_id_to_row = {x['id']: dict(x) for x in results}

        query_children = sa.text("""
            SELECT parent_id, child_id, order_id FROM gtdb_tree_children;
        """)
        results = db.execute(query_children).fetchall()

        d_parent_to_children = defaultdict(dict)
        d_child_to_parent = dict()
        for row in results:
            cur_parent_id = row['parent_id']
            cur_child_id = row['child_id']
            d_parent_to_children[cur_parent_id][cur_child_id] = row['order_id']
            d_child_to_parent[cur_child_id] = cur_parent_id

        return d_id_to_row, d_parent_to_children, d_child_to_parent
    finally:
        db.close()

def get_incorrect_rows(d_id_to_row, d_parent_to_children, d_child_to_parent):
    out = dict()

    for parent_id, row in d_id_to_row.items():

        cur_rank = row['type']
        parent_taxon = row['taxon']

        # We don't supply a count for species
        if cur_rank == 's':
            continue

        cur_n_desc_children = row['n_desc_children']

        # Collapse polyphyletic taxa for higher ranks
        child_taxa = set()
        for cur_child_id in d_parent_to_children[parent_id]:
            cur_child_taxon = d_id_to_row[cur_child_id]['taxon']
            if cur_rank in {'d', 'p', 'c', 'o'}:
                if cur_child_taxon[-2] == '_':
                    cur_child_taxon = cur_child_taxon[:-2]
            child_taxa.add(cur_child_taxon)

        # Check if the number of children is correct
        if len(child_taxa) != cur_n_desc_children:
            print(f'{parent_taxon}: {cur_n_desc_children} -> {len(child_taxa)}')
            out[parent_id] = len(child_taxa)

    return out

def update_rows(d_parent_id_to_correct_count):
    db = GtdbWebSession()
    try:
        for parent_id, correct_count in d_parent_id_to_correct_count.items():
            query = (
                sa.update(DbGtdbTree)
                .values(n_desc_children=correct_count)
                .where(DbGtdbTree.id == parent_id)
            )
            db.execute(query)
        db.commit()
    finally:
        db.close()


def main():
    """
    This script verifies that the child counts are correct
    (mainly for polyphyletic taxa) and updates them if they are not.
    """
    d_id_to_row, d_parent_to_children, d_child_to_parent = read_tree_rows()

    # Go through and make sure that the counts are correct
    d_parent_id_to_n_desc_children = get_incorrect_rows(d_id_to_row, d_parent_to_children, d_child_to_parent)

    update_rows(d_parent_id_to_n_desc_children)
    return


if __name__ == '__main__':
    main()
