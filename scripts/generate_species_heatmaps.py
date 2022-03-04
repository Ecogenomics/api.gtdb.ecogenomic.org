import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.getcwd()), '.env'))
os.environ['POSTGRES_USER'] = 'gtdb_rw'
os.environ['POSTGRES_PASS'] = 'kMBdwkvwpEXbAA8xsaw0chLa'

from collections import defaultdict
from api.db.models import MetadataTaxonomy, Genome, GenomeListContents, GtdbWebAni, GtdbWebSpeciesHeatmap
from tqdm import tqdm
from api.db import GtdbSession, GtdbWebSession
import sqlalchemy as sa

import scipy.cluster.hierarchy as sch
import numpy as np

from fastani import fastani


def get_all_data():
    db = GtdbSession()
    try:
        query = (
            sa.select([Genome.name, MetadataTaxonomy.gtdb_species, Genome.fasta_file_location,
                       MetadataTaxonomy.gtdb_representative]).
                select_from(sa.outerjoin(Genome, MetadataTaxonomy)).
                where(sa.or_(Genome.genome_source_id != 1,
                             Genome.id.in_(
                                 sa.select([GenomeListContents.genome_id]).
                                     select_from(GenomeListContents).
                                     where(GenomeListContents.list_id == 1152))
                             )
                      )
                .where(MetadataTaxonomy.gtdb_species != 's__')
                .where(Genome.id == MetadataTaxonomy.id)
                .order_by(MetadataTaxonomy.gtdb_species))

        out = defaultdict(set)
        paths = dict()
        sp_reps = dict()
        for row in db.execute(query):
            out[row.gtdb_species].add(row.name)
            paths[row.name] = row.fasta_file_location
            if row.gtdb_representative:
                sp_reps[row.gtdb_species] = row.name

        print(len(out))
        # out = {k: frozenset(v) for k, v in out.items() if 1 < len(v) < 5}
        out = {'s__Rhizobium leguminosarum': frozenset(out['s__Rhizobium leguminosarum'])}
        # currently processing 1 < len(v) < 5
        print(len(out))
        return out, paths, sp_reps
    finally:
        db.close()


def get_path(genome, gid_paths):
    if genome.startswith('GCA'):
        return os.path.join('/srv/db/gtdb/genomes/ncbi/release202/genbank', gid_paths[genome])
    elif genome.startswith('GCF'):
        return os.path.join('/srv/db/gtdb/genomes/ncbi/release202/refseq', gid_paths[genome])
    else:
        raise ValueError(genome)


def path_to_gid(path):
    return os.path.basename(path)[0:15]


def calculate_ordering_np(data):
    link = sch.linkage(data, optimal_ordering=True)
    tree = sch.dendrogram(link, no_plot=True, color_threshold=-np.inf)
    return tree['leaves']


def process_species(genomes, gid_paths):
    paths = set()

    for genome in genomes:
        paths.add(get_path(genome, gid_paths))

    # do fastani
    results = fastani(paths, paths, cpus=94, bidirectional=False, single_execution=False,
                      exe='/srv/home/uqamussi/.conda/envs/py38/bin/fastANI')

    out = list()
    for query_path, ref_d in results.as_dict().items():
        query_gid = path_to_gid(query_path)
        for ref_path, result in ref_d.items():
            ref_gid = path_to_gid(ref_path)
            out.append((query_gid, ref_gid, result.ani, result.n_frag, result.total_frag))

    return tuple(out)


def calc_ordering(data):
    gids = set()
    for row in data:
        gids.add(row[0])
        gids.add(row[1])

    out = dict()

    arr = np.zeros((len(gids), len(gids)))
    idx_to_gid = tuple(sorted(gids))
    gid_to_idx = {v: i for i, v in enumerate(sorted(gids))}
    for row in data:
        i = gid_to_idx[row[0]]
        j = gid_to_idx[row[1]]
        arr[i, j] = row[2]

    x = calculate_ordering_np(arr)
    y = calculate_ordering_np(arr.T)

    for gid, x_pos, y_pos in zip(idx_to_gid, x, y):
        out[gid] = (x_pos, y_pos)

    return out


def main():
    sp_clusters, gid_paths, sp_reps = get_all_data()

    gtdb_web_db = GtdbWebSession()
    try:

        for species, genomes in tqdm(sp_clusters.items()):
            ani = process_species(genomes, gid_paths)
            gid_orders = calc_ordering(ani)

            ani_objects = list()
            for row in ani:
                f'\t{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\t{row[4]}\n'
                ani_objects.append(GtdbWebAni(q=row[0], r=row[1], ani=row[2], n_frag=row[3], n_total_frag=row[4]))

            species_objects = list()
            for gid, (x_pos, y_pos) in gid_orders.items():
                species_objects.append(GtdbWebSpeciesHeatmap(species=species, gid=gid, x_order=x_pos, y_order=y_pos))

            gtdb_web_db.bulk_save_objects(ani_objects)
            gtdb_web_db.bulk_save_objects(species_objects)
            gtdb_web_db.commit()

    finally:
        gtdb_web_db.close()


if __name__ == '__main__':
    main()
