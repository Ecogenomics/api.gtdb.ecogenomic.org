if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

from collections import defaultdict

import sqlalchemy as sa
from sqlalchemy import insert
from tqdm import tqdm

from api.db import GtdbSession, GtdbWebSession
from api.db.models import MetadataTaxonomy, Genome, GtdbWebTaxonHist
from api.util.accession import canonical_gid
from api.util.collection import iter_batches


def read_taxonomy_table():
    db = GtdbSession()
    try:
        query = sa.select([
            Genome.name,
            MetadataTaxonomy.ncbi_taxonomy,
            MetadataTaxonomy.gtdb_domain,
            MetadataTaxonomy.gtdb_phylum,
            MetadataTaxonomy.gtdb_class,
            MetadataTaxonomy.gtdb_order,
            MetadataTaxonomy.gtdb_family,
            MetadataTaxonomy.gtdb_genus,
            MetadataTaxonomy.gtdb_species
        ]).join(Genome, Genome.id == MetadataTaxonomy.id)
        results = db.execute(query).fetchall()

        out = defaultdict(dict)
        for row in results:
            out[canonical_gid(row.name)] = dict(row)
        return dict(out)
    finally:
        db.close()


def convert_ncbi_tax_to_dict(ncbi_tax):
    ranks = ncbi_tax.strip().split(';')
    out = dict()
    for rank in ranks:
        if rank.startswith('x'):
            continue
        out[rank[0]] = rank
    assert (len(out)) == 7
    return out


def main():
    print('Reading data from GTDB metadata taxonomy')
    r214_taxonomy = read_taxonomy_table()
    print(f'Found {len(r214_taxonomy):,} genomes')

    # Create insert statements
    gids = sorted(r214_taxonomy)
    batches = list(iter_batches(gids, 100))

    db = GtdbWebSession()
    for batch in tqdm(batches):
        for gid in batch:
            d_cur_data = r214_taxonomy[gid]

            d_ncbi_tax = convert_ncbi_tax_to_dict(d_cur_data['ncbi_taxonomy'])

            stmt_ncbi = insert(GtdbWebTaxonHist).values(
                release_ver='NCBI',
                genome_id=gid,
                rank_domain=d_ncbi_tax['d'],
                rank_phylum=d_ncbi_tax['p'],
                rank_class=d_ncbi_tax['c'],
                rank_order=d_ncbi_tax['o'],
                rank_family=d_ncbi_tax['f'],
                rank_genus=d_ncbi_tax['g'],
                rank_species=d_ncbi_tax['s']
            )
            db.execute(stmt_ncbi)

            if d_cur_data['gtdb_domain'] == 'd__':
                continue
            if d_cur_data['gtdb_phylum'] == 'p__':
                continue
            if d_cur_data['gtdb_class'] == 'c__':
                continue
            if d_cur_data['gtdb_order'] == 'o__':
                continue
            if d_cur_data['gtdb_family'] == 'f__':
                continue
            if d_cur_data['gtdb_genus'] == 'g__':
                continue
            if d_cur_data['gtdb_species'] == 's__':
                continue

            stmt_214 = insert(GtdbWebTaxonHist).values(
                release_ver='R214',
                genome_id=gid,
                rank_domain=d_cur_data['gtdb_domain'],
                rank_phylum=d_cur_data['gtdb_phylum'],
                rank_class=d_cur_data['gtdb_class'],
                rank_order=d_cur_data['gtdb_order'],
                rank_family=d_cur_data['gtdb_family'],
                rank_genus=d_cur_data['gtdb_genus'],
                rank_species=d_cur_data['gtdb_species']
            )
            db.execute(stmt_214)

        db.commit()
    return


if __name__ == '__main__':
    main()
