import re
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.config import GTDB_RELEASES
from api.db.models import SurveyGenomes, GtdbWebTaxonHist, GtdbWebLpsnUrl, Genome, MetadataNcbi, MetadataGene, \
    MetadataNucleotide, MetadataTaxonomy, MetadataTypeMaterial, GtdbWebGenomeTaxId, GtdbTypeView
from api.exceptions import HttpNotFound, HttpBadRequest
from api.model.genome import GenomeMetadata, GenomeTaxonHistory, GenomeCard, GenomeBase, GenomeMetadataNucleotide, \
    GenomeMetadataGene, GenomeMetadataNcbi, GenomeMetadataTaxonomy, GenomeNcbiTaxon, GenomeMetadataTypeMaterial
from api.util.accession import canonical_gid

RE_SURVEY = re.compile(r'((?:GC[FA]_)?\d{9}(?:\.\d)?)')


def is_surveillance_genome(gid: str, db: Session) -> Optional[str]:
    # Check if this is a surveillance genome
    hit = RE_SURVEY.search(gid)
    if hit:
        query = sa.select([SurveyGenomes.canonical_gid]).where(SurveyGenomes.canonical_gid.contains(hit.group(1)))
        results = db.execute(query).fetchone()
        if results:
            return results.canonical_gid.strip()
    return None


def genome_metadata(gid: str, db: Session) -> GenomeMetadata:
    survey_hit = is_surveillance_genome(gid, db)
    return GenomeMetadata(accession=survey_hit or gid,
                          isNcbiSurveillance=survey_hit is not None)


def genome_taxon_history(gid: str, db: Session) -> List[GenomeTaxonHistory]:
    query = sa.select([GtdbWebTaxonHist.release_ver,
                       GtdbWebTaxonHist.rank_domain,
                       GtdbWebTaxonHist.rank_phylum,
                       GtdbWebTaxonHist.rank_class,
                       GtdbWebTaxonHist.rank_order,
                       GtdbWebTaxonHist.rank_family,
                       GtdbWebTaxonHist.rank_genus,
                       GtdbWebTaxonHist.rank_species]) \
        .where(sa.and_(GtdbWebTaxonHist.genome_id == canonical_gid(gid),
                       GtdbWebTaxonHist.release_ver != 'NCBI'))
    out = list()
    for row in db.execute(query):
        out.append(GenomeTaxonHistory(release=row.release_ver.strip(),
                                      d=row.rank_domain,
                                      p=row.rank_phylum,
                                      c=row.rank_class,
                                      o=row.rank_order,
                                      f=row.rank_family,
                                      g=row.rank_genus,
                                      s=row.rank_species))
    return sorted(out, key=lambda x: GTDB_RELEASES.index(x.release), reverse=True)


def maybe_get_lspn_url(species: str, db_web: Session) -> Optional[str]:
    # Load the LSPN URL if it exists
    query = sa.select([GtdbWebLpsnUrl.lpsn_url]).where(GtdbWebLpsnUrl.gtdb_species == species)
    results = db_web.execute(query).fetchall()
    if len(results) == 1:
        return results[0].lpsn_url
    else:
        return None


def rank_count(rank, db_gtdb):
    """Returns the number of genomes in a given GTDB rank."""
    if rank is None:
        raise HttpBadRequest('You must enter a GTDB rank.')

    if len(rank) <= 3 or rank[0:3] not in {'d__', 'p__', 'c__', 'o__', 'f__', 'g__', 's__'}:
        raise HttpBadRequest('Malformed GTDB rank.')

    # Determine which rank to query.
    rank_to_col = {'d__': MetadataTaxonomy.gtdb_domain,
                   'p__': MetadataTaxonomy.gtdb_phylum,
                   'c__': MetadataTaxonomy.gtdb_class,
                   'o__': MetadataTaxonomy.gtdb_order,
                   'f__': MetadataTaxonomy.gtdb_family,
                   'g__': MetadataTaxonomy.gtdb_genus,
                   's__': MetadataTaxonomy.gtdb_species}

    # Query for the taxonomy history
    query = (
        sa.select([sa.func.count('*')]).
        select_from(MetadataTaxonomy).
        where(rank_to_col[rank[0:3]] == rank)
    )
    cnt = db_gtdb.execute(query).scalar()
    return {'count': cnt}


def taxonomy_species_cluster_stats(species, db_gtdb):
    res_rep_qry = (
        sa.select([MetadataNcbi.ncbi_genbank_assembly_accession.label('name'),
                   MetadataTaxonomy.gtdb_representative]).
        select_from(sa.join(Genome, MetadataTaxonomy).join(MetadataNcbi)).
        where(MetadataTaxonomy.gtdb_species == species).
        where(MetadataTaxonomy.gtdb_genome_representative != None)
    )
    qry_out = db_gtdb.execute(res_rep_qry)
    rows = [(dict(row)) for row in qry_out]
    cluster_size = len(rows)

    rep = [x for x in rows if x['gtdb_representative']]
    if len(rep) != 1:
        raise HttpBadRequest('More than one representative genome found.')

    rep_gid = rep[0]['name']
    return {'representative': rep_gid, 'cluster_size': cluster_size}


def genome_card(accession: str, db_gtdb: Session, db_web: Session) -> GenomeCard:
    genome = db_gtdb.query(Genome).filter_by(id_at_source=accession).first()
    if genome is None:
        metadata_ncbi_gca = db_gtdb.query(MetadataNcbi).filter_by(ncbi_genbank_assembly_accession=accession).first()
        if metadata_ncbi_gca is not None:
            genome = db_gtdb.query(Genome).filter_by(id=metadata_ncbi_gca.id).first()
            genome = db_gtdb.query(Genome).filter_by(id_at_source=genome.id_at_source).first()
    if genome is None:
        genome = db_gtdb.query(Genome).filter(Genome.name.like("%({0})".format(accession))).first()
    if genome is None:
        raise HttpNotFound('Genome not found')

    metadata_gene = db_gtdb.query(MetadataGene).filter_by(id=genome.id).first()
    metadata_ncbi = db_gtdb.query(MetadataNcbi).filter_by(id=genome.id).first()
    metadata_nucleotide = db_gtdb.query(MetadataNucleotide).filter_by(id=genome.id).first()
    metadata_taxonomy = db_gtdb.query(MetadataTaxonomy).filter_by(id=genome.id).first()
    metadata_type_material = db_gtdb.query(MetadataTypeMaterial).filter_by(id=genome.id).first()
    gtdb_type_view = db_gtdb.query(GtdbTypeView).filter_by(id=genome.id).first()

    m = re.search('\((UBA\d+)\)', genome.name)
    subunit_summary_list = []

    if metadata_gene.lsu_5s_count > 0:
        subunit_summary_list.append('5S')
    if metadata_gene.ssu_count > 0:
        subunit_summary_list.append('16S')
    if metadata_gene.lsu_23s_count > 0:
        subunit_summary_list.append('23S')
    subunit_summary = '/'.join(subunit_summary_list)
    if m:
        ubanumber = m.group(1)
    else:
        ubanumber = ''
    try:
        species_cluster_count = rank_count(metadata_taxonomy.gtdb_species, db_gtdb)['count']
    except Exception:
        species_cluster_count = None

    # Get the species representative.
    try:
        species_cluster_info = taxonomy_species_cluster_stats(metadata_taxonomy.gtdb_species, db_gtdb)
        species_rep = species_cluster_info['representative']
    except Exception:
        species_rep = 'Error'

    # Load the LSPN URL if it exists
    lpsn_url = maybe_get_lspn_url(metadata_taxonomy.gtdb_species, db_web)

    taxid_resp = db_web.query(GtdbWebGenomeTaxId).filter_by(genome_id=genome.id_at_source).all()

    ncbi_taxonomy_filtered = list()
    ncbi_taxonomy_unfiltered = list()

    if len(taxid_resp) == 1:
        ranks_ncbi = taxid_resp[0].payload
        rank_list = []
        for idv_rank in metadata_taxonomy.ncbi_taxonomy.split(';'):
            if idv_rank in ranks_ncbi:
                rank_list.append(
                    '<a target="_blank" href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + ranks_ncbi.get(
                        idv_rank) + '">' + idv_rank + '</a>')
                ncbi_taxonomy_filtered.append(GenomeNcbiTaxon(taxon=idv_rank, taxonId=ranks_ncbi.get(idv_rank)))
            else:
                rank_list.append(idv_rank)
                ncbi_taxonomy_filtered.append(GenomeNcbiTaxon(taxon=idv_rank))

        link_ncbi_taxonomy = '; '.join(rank_list)
        rank_list_unfiltered = []
        for idv_rank in metadata_taxonomy.ncbi_taxonomy_unfiltered.split(';'):
            if idv_rank in ranks_ncbi:
                rank_list_unfiltered.append(
                    '<a target="_blank" href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + ranks_ncbi.get(
                        idv_rank) + '">' + idv_rank + '</a>')
                ncbi_taxonomy_unfiltered.append(GenomeNcbiTaxon(taxon=idv_rank, taxonId=ranks_ncbi.get(idv_rank)))
            else:
                rank_list_unfiltered.append(idv_rank)
                ncbi_taxonomy_unfiltered.append(GenomeNcbiTaxon(taxon=idv_rank))
        link_ncbi_taxonomy_unfiltered = '; '.join(rank_list_unfiltered)
    else:
        if metadata_taxonomy.ncbi_taxonomy is not None:
            ncbi_taxonomy_filtered.append(GenomeNcbiTaxon(taxon=metadata_taxonomy.ncbi_taxonomy))
        else:
            ncbi_taxonomy_filtered = None
        if metadata_taxonomy.ncbi_taxonomy_unfiltered is not None:
            ncbi_taxonomy_unfiltered.append(GenomeNcbiTaxon(taxon=metadata_taxonomy.ncbi_taxonomy_unfiltered))
        else:
            ncbi_taxonomy_unfiltered = None

        # legacy.
        link_ncbi_taxonomy_unfiltered = metadata_taxonomy.ncbi_taxonomy_unfiltered
        link_ncbi_taxonomy = metadata_taxonomy.ncbi_taxonomy

    # dont need to account for ubas now
    if metadata_ncbi.ncbi_genbank_assembly_accession is not None and len(
            metadata_ncbi.ncbi_genbank_assembly_accession) > 1:
        out_accession = metadata_ncbi.ncbi_genbank_assembly_accession
    else:
        out_accession = genome.id_at_source

    out_metadata_gene = GenomeMetadataGene(checkm_completeness=metadata_gene.checkm_completeness,
                                           checkm_contamination=metadata_gene.checkm_contamination,
                                           checkm_strain_heterogeneity=metadata_gene.checkm_strain_heterogeneity,
                                           lsu_5s_count=metadata_gene.lsu_5s_count,
                                           ssu_count=metadata_gene.ssu_count,
                                           lsu_23s_count=metadata_gene.lsu_23s_count,
                                           protein_count=metadata_gene.protein_count,
                                           coding_density=metadata_gene.coding_density)

    out_metadata_type_material = GenomeMetadataTypeMaterial(
        gtdbTypeDesignation=metadata_type_material.gtdb_type_designation,
        gtdbTypeDesignationSources=metadata_type_material.gtdb_type_designation_sources,
        lpsnTypeDesignation=metadata_type_material.lpsn_type_designation,
        dsmzTypeDesignation=metadata_type_material.dsmz_type_designation,
        lpsnPriorityYear=metadata_type_material.lpsn_priority_year,
        gtdbTypeSpeciesOfGenus=gtdb_type_view.gtdb_genus_type_species)

    out_metadata_ncbi = GenomeMetadataNcbi(
        ncbi_genbank_assembly_accession=metadata_ncbi.ncbi_genbank_assembly_accession,
        ncbi_strain_identifiers=metadata_ncbi.ncbi_strain_identifiers,
        ncbi_assembly_level=metadata_ncbi.ncbi_assembly_level,
        ncbi_assembly_name=metadata_ncbi.ncbi_assembly_name,
        ncbi_assembly_type=metadata_ncbi.ncbi_assembly_type,
        ncbi_bioproject=metadata_ncbi.ncbi_bioproject,
        ncbi_biosample=metadata_ncbi.ncbi_biosample,
        ncbi_country=metadata_ncbi.ncbi_country,
        ncbi_date=metadata_ncbi.ncbi_date,
        ncbi_genome_category=metadata_ncbi.ncbi_genome_category,
        ncbi_genome_representation=metadata_ncbi.ncbi_genome_representation,
        ncbi_isolate=metadata_ncbi.ncbi_isolate,
        ncbi_isolation_source=metadata_ncbi.ncbi_isolation_source,
        ncbi_lat_lon=metadata_ncbi.ncbi_lat_lon,
        ncbi_molecule_count=metadata_ncbi.ncbi_molecule_count,
        ncbi_cds_count=metadata_ncbi.ncbi_cds_count,
        ncbi_refseq_category=metadata_ncbi.ncbi_refseq_category,
        ncbi_seq_rel_date=metadata_ncbi.ncbi_seq_rel_date,
        ncbi_spanned_gaps=metadata_ncbi.ncbi_spanned_gaps,
        ncbi_species_taxid=metadata_ncbi.ncbi_species_taxid,
        ncbi_ssu_count=metadata_ncbi.ncbi_ssu_count,
        ncbi_submitter=metadata_ncbi.ncbi_submitter,
        ncbi_taxid=metadata_ncbi.ncbi_taxid,
        ncbi_total_gap_length=metadata_ncbi.ncbi_total_gap_length,
        ncbi_translation_table=metadata_ncbi.ncbi_translation_table,
        ncbi_trna_count=metadata_ncbi.ncbi_trna_count,
        ncbi_unspanned_gaps=metadata_ncbi.ncbi_unspanned_gaps,
        ncbi_version_status=metadata_ncbi.ncbi_version_status,
        ncbi_wgs_master=metadata_ncbi.ncbi_wgs_master)

    out_metadata_taxonomy = GenomeMetadataTaxonomy(ncbi_taxonomy=metadata_taxonomy.ncbi_taxonomy,
                                                   ncbi_taxonomy_unfiltered=metadata_taxonomy.ncbi_taxonomy_unfiltered,
                                                   gtdb_representative=metadata_taxonomy.gtdb_representative,
                                                   gtdb_genome_representative=metadata_taxonomy.gtdb_genome_representative,
                                                   ncbi_type_material_designation=metadata_taxonomy.ncbi_type_material_designation,
                                                   gtdbDomain=metadata_taxonomy.gtdb_domain,
                                                   gtdbPhylum=metadata_taxonomy.gtdb_phylum,
                                                   gtdbClass=metadata_taxonomy.gtdb_class,
                                                   gtdbOrder=metadata_taxonomy.gtdb_order,
                                                   gtdbFamily=metadata_taxonomy.gtdb_family,
                                                   gtdbGenus=metadata_taxonomy.gtdb_genus,
                                                   gtdbSpecies=metadata_taxonomy.gtdb_species)

    return GenomeCard(genome=GenomeBase(accession=out_accession,
                                        name=genome.name),
                      metadata_nucleotide=GenomeMetadataNucleotide(trna_aa_count=metadata_nucleotide.trna_aa_count,
                                                                   contig_count=metadata_nucleotide.contig_count,
                                                                   n50_contigs=metadata_nucleotide.n50_contigs,
                                                                   longest_contig=metadata_nucleotide.longest_contig,
                                                                   scaffold_count=metadata_nucleotide.scaffold_count,
                                                                   n50_scaffolds=metadata_nucleotide.n50_scaffolds,
                                                                   longest_scaffold=metadata_nucleotide.longest_scaffold,
                                                                   genome_size=metadata_nucleotide.genome_size,
                                                                   gc_percentage=metadata_nucleotide.gc_percentage,
                                                                   ambiguous_bases=metadata_nucleotide.ambiguous_bases),
                      metadata_gene=out_metadata_gene,
                      metadata_ncbi=out_metadata_ncbi,
                      metadataTaxonomy=out_metadata_taxonomy,
                      gtdbTypeDesignation=metadata_type_material.gtdb_type_designation,
                      subunit_summary=subunit_summary,
                      speciesClusterCount=species_cluster_count,
                      metadata_type_material=out_metadata_type_material,
                      link_ncbi_taxonomy=link_ncbi_taxonomy,
                      link_ncbi_taxonomy_unfiltered=link_ncbi_taxonomy_unfiltered,
                      speciesRepName=species_rep,
                      lpsnUrl=lpsn_url,
                      ncbiTaxonomyFiltered=ncbi_taxonomy_filtered,
                      ncbiTaxonomyUnfiltered=ncbi_taxonomy_unfiltered)
