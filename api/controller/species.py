from typing import List

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.db.models import Genome, MetadataNcbi, MetadataTaxonomy, GtdbTaxonomyView, GenomeListContents
from api.exceptions import HttpInternalServerError, HttpBadRequest
from api.model.species import SpeciesCluster, SpeciesClusterGenome


def get_species_cluster(species: str, db: Session) -> SpeciesCluster:
    """Returns the number of genomes in each species cluster."""

    # Get each of the genomes in the species cluster
    base_query = (
        sa.select([Genome.id,
                   MetadataNcbi.ncbi_organism_name,
                   sa.func.replace(MetadataTaxonomy.ncbi_taxonomy, ';', '; ').label('ncbi_taxonomy'),
                   MetadataTaxonomy.gtdb_domain,
                   MetadataTaxonomy.gtdb_phylum,
                   MetadataTaxonomy.gtdb_class,
                   MetadataTaxonomy.gtdb_order,
                   MetadataTaxonomy.gtdb_family,
                   MetadataTaxonomy.gtdb_genus,
                   MetadataTaxonomy.gtdb_species,
                   MetadataTaxonomy.gtdb_representative,
                   MetadataTaxonomy.ncbi_type_material_designation,
                   MetadataNcbi.ncbi_genbank_assembly_accession
                   ]).
            select_from(sa.outerjoin(Genome, MetadataTaxonomy).
                        outerjoin(GtdbTaxonomyView).
                        outerjoin(MetadataNcbi)).
            where(sa.or_(Genome.genome_source_id != 1,
                         Genome.id.in_(
                             sa.select([GenomeListContents.genome_id]).
                                 select_from(GenomeListContents).
                                 where(GenomeListContents.list_id == 1152))
                         )
                  )
    )
    query = base_query.where(MetadataTaxonomy.gtdb_species == f's__{species}')

    # Convert to objects
    species_cluster_genomes = list()
    d, p, c, o, f, g, s = set(), set(), set(), set(), set(), set(), set()
    for row in db.execute(query):
        d.add(row.gtdb_domain)
        p.add(row.gtdb_phylum)
        c.add(row.gtdb_class)
        o.add(row.gtdb_order)
        f.add(row.gtdb_family)
        g.add(row.gtdb_genus)
        s.add(row.gtdb_species)
        species_cluster_genomes.append(
            SpeciesClusterGenome(accession=row.ncbi_genbank_assembly_accession,
                                 ncbi_org_name=row.ncbi_organism_name,
                                 ncbi_tax=row.ncbi_taxonomy,
                                 gtdb_species_rep=row.gtdb_representative,
                                 ncbi_type_material=row.ncbi_type_material_designation)
        )

    # Validation
    if len(species_cluster_genomes) == 0:
        raise HttpBadRequest(f'No genomes found for species {species}')
    if len(d) + len(p) + len(c) + len(o) + len(f) + len(g) + len(s) != 7:
        raise HttpInternalServerError(f'Too many taxonomic levels for species {species}')
    cluster = SpeciesCluster(name=species, genomes=species_cluster_genomes,
                             d=list(d)[0], p=list(p)[0], c=list(c)[0], o=list(o)[0],
                             f=list(f)[0], g=list(g)[0], s=list(s)[0])
    return cluster


def util_species_all(db: Session) -> List[str]:
    out = list()

    query = (
        sa.select([MetadataTaxonomy.gtdb_species]).
            select_from(sa.outerjoin(Genome, MetadataTaxonomy).
                        outerjoin(GtdbTaxonomyView).
                        outerjoin(MetadataNcbi)).
            where(sa.or_(Genome.genome_source_id != 1,
                         Genome.id.in_(
                             sa.select([GenomeListContents.genome_id]).
                                 select_from(GenomeListContents).
                                 where(GenomeListContents.list_id == 1152))
                         )
                  )
            .where(MetadataTaxonomy.gtdb_species != 's__')
    ).order_by(MetadataTaxonomy.gtdb_species).distinct()

    rows = db.execute(query)
    return [str(x.gtdb_species) for x in rows]

#
# def c_species_heatmap(species: str, db_web: Session, db_gtdb: Session) -> SpeciesHeatmap:
#     # Get the label ordering
#     species_order_query = (
#         sa.select([GtdbWebSpeciesHeatmap.gid, GtdbWebSpeciesHeatmap.x_order, GtdbWebSpeciesHeatmap.y_order]).
#             where(GtdbWebSpeciesHeatmap.species == species)
#     )
#     species_order_results = db_web.execute(species_order_query)
#
#     d_x_labels, d_y_labels = dict(), dict()
#     for row in species_order_results:
#         d_x_labels[row.gid] = row.x_order
#         d_y_labels[row.gid] = row.y_order
#     x_labels = [k for k, v in sorted(d_x_labels.items(), key=lambda x: x[1])]
#     y_labels = [k for k, v in sorted(d_y_labels.items(), key=lambda x: x[1])]
#
#     # Get the data
#     species_data_query = (
#         sa.select([GtdbWebAni.q, GtdbWebAni.r, GtdbWebAni.ani, GtdbWebAni.n_frag, GtdbWebAni.n_total_frag])
#             .where(GtdbWebAni.q.in_(
#             sa.select([GtdbWebSpeciesHeatmap.gid]).
#                 where(GtdbWebSpeciesHeatmap.species == species)
#         ))
#             .where(GtdbWebAni.r.in_(
#             sa.select([GtdbWebSpeciesHeatmap.gid]).
#                 where(GtdbWebSpeciesHeatmap.species == species)
#         ))
#     )
#     species_data_results = db_web.execute(species_data_query)
#
#     # Get the species representative
#     # Get each of the genomes in the species cluster
#     rep_query = (
#         sa.select([Genome.name, MetadataTaxonomy.gtdb_representative]).
#             select_from(sa.join(Genome, MetadataTaxonomy)).
#             where(MetadataTaxonomy.gtdb_species == species).
#             where(MetadataTaxonomy.gtdb_representative == True).
#             where(sa.or_(Genome.genome_source_id != 1,
#                          Genome.id.in_(
#                              sa.select([GenomeListContents.genome_id]).
#                                  select_from(GenomeListContents).
#                                  where(GenomeListContents.list_id == 1152))
#                          )
#                   )
#     )
#     rep_results = list(db_gtdb.execute(rep_query))
#     if len(rep_results) == 1:
#         gtdb_rep = rep_results[0].name
#     else:
#         print('Unable to determine representative genome for species {}'.format(species))
#         gtdb_rep = None
#
#     # Output the data
#     return SpeciesHeatmap(
#         name=species,
#         xLabels=x_labels,
#         yLabels=y_labels,
#         data=[tuple(x) for x in species_data_results],
#         gtdbRep=gtdb_rep
#     )
