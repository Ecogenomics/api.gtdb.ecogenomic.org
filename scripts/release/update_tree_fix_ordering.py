if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
from collections import defaultdict

import sqlalchemy as sa

from api.db import GtdbWebSession
from api.db.models import DbGtdbTreeChildren

TS_SPECIES = frozenset({'type_strain_of_species', 'type_strain_of_heterotypic_synonym', 'type_strain_of_subspecies'})

TS_SP_ORDER = {
    'type_strain_of_species': 0,
    'type_strain_of_heterotypic_synonym': 2,
    'type_strain_of_subspecies': 1
}


def read_tree_rows():
    db = GtdbWebSession()
    try:
        query = sa.text("""
            select id, taxon, type, is_rep, type_material
            from gtdb_tree
            where type in ('genome', 's', 'g', 'f');
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
            if cur_child_id in d_id_to_row or cur_parent_id in d_id_to_row:
                d_parent_to_children[cur_parent_id][cur_child_id] = row['order_id']
                d_child_to_parent[cur_child_id] = cur_parent_id

        return d_id_to_row, d_parent_to_children, d_child_to_parent
    finally:
        db.close()


def get_parent_ids_where_type_species_of_genus_wrong(d_id_to_row, d_parent_to_children, d_child_to_parent):
    out = set()

    # Identify the IDs associated with non-null  is_rep or type_material values
    # Identify child rows where the type_material is type species of genus
    parent_ids_with_type_genus_children = set()
    for row in d_id_to_row.values():
        if row['type_material'] == 'type_species':
            cur_parent_id = d_child_to_parent[row['id']]
            parent_ids_with_type_genus_children.add(cur_parent_id)

    # Go through each parent and check the ordering is correct
    for cur_parent_id in parent_ids_with_type_genus_children:
        # Set vars
        d_cur_children = d_parent_to_children[cur_parent_id]

        # Obtain the number of type species of genus in the parent
        n_type_sp = sum([d_id_to_row[x]['type_material'] == 'type_species' for x in d_cur_children])

        # Sort the children by the order id
        child_ids_sorted = [x[0] for x in sorted(d_cur_children.items(), key=lambda x: x[1])]
        child_type_mat = [d_id_to_row[x]['type_material'] for x in child_ids_sorted]

        # We would then expect ALL of the values up to n_type_sp to be 'type_species'
        child_type_mat_subset = child_type_mat[:n_type_sp]
        if not all([x == 'type_species' for x in child_type_mat_subset]):
            out.add(cur_parent_id)
    return out


def set_ordering(parent_id, child_ids_ordered):
    db = GtdbWebSession()
    try:
        for order_id, child_id in enumerate(child_ids_ordered):
            # Update the db
            query = (
                sa.update(DbGtdbTreeChildren)
                .values(order_id=order_id)
                .where(DbGtdbTreeChildren.parent_id == parent_id)
                .where(DbGtdbTreeChildren.child_id == child_id)
            )
            db.execute(query)
        db.commit()
    finally:
        db.close()


def update_wrong_sp_of_genus_ordering(parent_ids, d_parent_to_children, d_id_to_row):
    for cur_parent_id in parent_ids:
        d_cur_children = d_parent_to_children[cur_parent_id]
        child_ids_sorted = [x[0] for x in sorted(d_cur_children.items(), key=lambda x: x[1])]
        child_ids_data = [d_id_to_row[x] for x in child_ids_sorted]

        # Preserve the existing order but put the type genus first
        first_part = list()
        second_part = list()
        for d_cur_child_data in child_ids_data:
            if d_cur_child_data['type_material'] == 'type_species':
                first_part.append(d_cur_child_data['id'])
            else:
                second_part.append(d_cur_child_data['id'])
        final_ordering = first_part + second_part

        # Update the database
        set_ordering(cur_parent_id, final_ordering)

    return


def get_parent_ids_wrong_strains(d_id_to_row, d_parent_to_children, d_child_to_parent):
    out = dict()
    parent_ids_eligble = set()
    for row in d_id_to_row.values():
        if row['type_material'] in TS_SPECIES:
            cur_parent_id = d_child_to_parent[row['id']]
            parent_ids_eligble.add(cur_parent_id)

    # Go through each parent and check the ordering is correct
    for cur_parent_id in parent_ids_eligble:
        # Set vars
        d_cur_children = d_parent_to_children[cur_parent_id]

        # Sort the children by the order id
        child_ids_sorted = [x[0] for x in sorted(d_cur_children.items(), key=lambda x: x[1])]

        # Generate the expected ordering
        first, second, third, fourth, fifth = list(), list(), list(), list(), list()
        for child_id in child_ids_sorted:
            cur_child_row = d_id_to_row[child_id]
            if cur_child_row['is_rep'] is True:
                first.append(child_id)
            elif cur_child_row['type_material'] == 'type_strain_of_species':
                second.append(child_id)
            elif cur_child_row['type_material'] == 'type_strain_of_subspecies':
                third.append(child_id)
            elif cur_child_row['type_material'] == 'type_strain_of_heterotypic_synonym':
                fourth.append(child_id)
            else:
                fifth.append(child_id)
        final_ordering = first + second + third + fourth + fifth

        assert len(final_ordering) == len(child_ids_sorted)

        if final_ordering != child_ids_sorted:
            out[cur_parent_id] = final_ordering
    return out


def update_wrong_strains(d_id_to_row, d_parent_to_children, d_child_to_parent):
    d_parent_id_to_correct_ordering = get_parent_ids_wrong_strains(d_id_to_row, d_parent_to_children, d_child_to_parent)

    # Update the db
    for cur_parent_id, final_ordering in d_parent_id_to_correct_ordering.items():
        set_ordering(cur_parent_id, final_ordering)
    return


def main():
    """
    This script updates the database to set the correct ordering in the tree
    for type species of genus and type strains of species, subspecies, and heterotypic synonyms.
    """

    d_id_to_row, d_parent_to_children, d_child_to_parent = read_tree_rows()

    type_sp_of_genus_wrong_parent_ids = get_parent_ids_where_type_species_of_genus_wrong(
        d_id_to_row,
        d_parent_to_children,
        d_child_to_parent
    )
    update_wrong_sp_of_genus_ordering(type_sp_of_genus_wrong_parent_ids, d_parent_to_children, d_id_to_row)

    update_wrong_strains(d_id_to_row, d_parent_to_children, d_child_to_parent)

    return


if __name__ == '__main__':
    main()
