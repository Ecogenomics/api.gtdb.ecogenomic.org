"""
This script updates the tree view with the taxonomic information obtained
from the common database (i.e. Bergeys, LPSN, NCBI, SeqCode).
"""

if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import sqlalchemy as sa
from tqdm import tqdm

from api.db import GtdbCommonSession, GtdbWebSession, GtdbSession
from api.db.models import GtdbWebUrlSeqcode


def load_seqcode():
    db = GtdbCommonSession()
    try:
        query = sa.text("""
        SELECT seq.id,
           seq.name AS taxon,
           seq.rank AS rank,
           d.name AS sc_domain,
           p.name AS sc_phylum,
           c.name AS sc_class,
           o.name AS sc_order,
           f.name AS sc_family,
           g.name AS sc_genus,
           s.name AS sc_species
        FROM seqcode_html seq
                 LEFT JOIN seqcode_html d ON d.id = seq.domain_id
                 LEFT JOIN seqcode_html p ON p.id = seq.phylum_id
                 LEFT JOIN seqcode_html c ON c.id = seq.class_id
                 LEFT JOIN seqcode_html o ON o.id = seq.order_id
                 LEFT JOIN seqcode_html f ON f.id = seq.family_id
                 LEFT JOIN seqcode_html g ON g.id = seq.genus_id
                 LEFT JOIN seqcode_html s ON s.id = seq.species_id
        WHERE seq.name IS NOT NULL
        ORDER BY seq.id
        """)
        results = db.execute(query).fetchall()
        return {x.id: x._asdict() for x in results}
    finally:
        db.close()


def convert_tree_to_nested_dict(d_taxon_to_id, d_id_to_taxon, d_parent_to_children, next_taxon):
    if next_taxon.startswith('s__'):
        return

    # Find all children associated with this taxon
    parent_id = d_taxon_to_id[next_taxon]
    children = dict()
    for child_id in d_parent_to_children[parent_id]:
        children[d_id_to_taxon[child_id]] = convert_tree_to_nested_dict(d_taxon_to_id, d_id_to_taxon,
                                                                        d_parent_to_children, d_id_to_taxon[child_id])
    return {next_taxon: children}


def load_taxstrings():
    db = GtdbSession()
    try:
        query = sa.text("""
            SELECT DISTINCT gtdb_domain, gtdb_phylum, gtdb_class, gtdb_order, gtdb_family, gtdb_genus, gtdb_species
            FROM metadata_taxonomy;
        """)
        results = db.execute(query).fetchall()
        out = dict()
        out2 = dict()
        for row in results:
            d = row.gtdb_domain
            p = row.gtdb_phylum
            c = row.gtdb_class
            o = row.gtdb_order
            f = row.gtdb_family
            g = row.gtdb_genus
            s = row.gtdb_species

            taxstring_rev = list(reversed((d, p, c, o, f, g, s)))
            for i in range(len(taxstring_rev) - 1):
                out2[taxstring_rev[i]] = {x[0]: x for x in reversed(taxstring_rev[i + 1:])}

            if d not in out:
                out[d] = dict()
            if p not in out[d]:
                out[d][p] = dict()
            if c not in out[d][p]:
                out[d][p][c] = dict()
            if o not in out[d][p][c]:
                out[d][p][c][o] = dict()
            if f not in out[d][p][c][o]:
                out[d][p][c][o][f] = dict()
            if g not in out[d][p][c][o][f]:
                out[d][p][c][o][f][g] = dict()
            if s not in out[d][p][c][o][f][g]:
                out[d][p][c][o][f][g][s] = None

        return out, out2
    finally:
        db.close()


def load_tree():
    db = GtdbWebSession()
    try:
        # Obtain the taxon IDs from the tree table
        query_parents = sa.text("""
            SELECT t.id, t.taxon
            FROM gtdb_tree t
            WHERE t.type IN ('d', 'p', 'c', 'o', 'f', 'g', 's');
        """)
        results_parents = db.execute(query_parents).fetchall()
        d_taxon_to_id = {x.taxon: x.id for x in results_parents}
        return d_taxon_to_id
    finally:
        db.close()


def get_existing_seqcode_annotations():
    out = dict()
    db = GtdbWebSession()
    try:
        query = (sa.select(GtdbWebUrlSeqcode.id, GtdbWebUrlSeqcode.url))
        results = db.execute(query).fetchall()
        for row in results:
            out[row.id] = row.url
    finally:
        db.close()
    return out


def process_seqcode_annotations(d_taxon_to_id):
    d_seqcode = load_seqcode()
    existing_urls = get_existing_seqcode_annotations()

    to_update = dict()
    to_insert = dict()

    # Iterate over each seqcode annotation and try find a GTDB mapping
    for row in d_seqcode.values():

        # Must have a rank to continue
        if row['rank'] is None:
            continue

        if row['taxon'].startswith('Candidatus'):
            taxon = row['taxon'][11:]
        else:
            taxon = row['taxon']

        taxon = f'{row["rank"][0]}__{taxon}'
        tree_id = d_taxon_to_id.get(taxon)

        if tree_id is None:
            continue

        out_url = f'https://seqco.de/i:{row["id"]}'
        cur_existing = existing_urls.get(tree_id)
        if cur_existing:
            if cur_existing != out_url:
                to_update[tree_id] = out_url
        else:
            to_insert[tree_id] = out_url

    db = GtdbWebSession()
    try:
        # Update the records
        for tree_id, url in tqdm(to_update.items(), desc='Updating URLs'):
            query = sa.update(GtdbWebUrlSeqcode).where(GtdbWebUrlSeqcode.id == tree_id).values(url=url)
            db.execute(query)

        # Insert the others
        for tree_id, url in tqdm(to_insert.items(), desc='Inserting URLs'):
            query = sa.insert(GtdbWebUrlSeqcode).values(id=tree_id, url=url)
            db.execute(query)

        db.commit()

    finally:
        db.close()
    return


def main():
    # Load the GTDB information
    d_taxon_to_id = load_tree()

    # Process the SeqCode annotations
    process_seqcode_annotations(d_taxon_to_id)

    return


if __name__ == '__main__':
    main()
