from sqlalchemy import CHAR, Boolean, Column, Date, DateTime, Float, \
    ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, BIGINT
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from api.db import GtdbBase, GtdbWebBase


class GenomeSource(GtdbBase):  # OK
    __tablename__ = 'genome_sources'

    id = Column(Integer, primary_key=True, server_default=text("nextval('genome_sources_id_seq'::regclass)"))
    name = Column(Text, nullable=False, unique=True)
    external_id_prefix = Column(Text, nullable=False, unique=True)
    last_auto_id = Column(Integer, nullable=False, server_default=text("0"))
    user_editable = Column(Boolean, nullable=False, server_default=text("false"))


class Genome(GtdbBase):  # OK
    __tablename__ = 'genomes'
    __table_args__ = (
        UniqueConstraint('genome_source_id', 'id_at_source'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('genomes_id_seq'::regclass)"))
    name = Column(Text, nullable=False)
    description = Column(Text)
    owned_by_root = Column(Boolean, nullable=False, server_default=text("false"))
    owner_id = Column(ForeignKey('users.id', onupdate='CASCADE'))
    fasta_file_location = Column(Text, nullable=False)
    fasta_file_sha256 = Column(Text, nullable=False)
    genome_source_id = Column(ForeignKey('genome_sources.id', onupdate='CASCADE'), nullable=False)
    id_at_source = Column(Text, nullable=False)
    date_added = Column(DateTime, nullable=False)
    has_changed = Column(Boolean, nullable=False, server_default=text("true"))
    last_update = Column(Date)
    genes_file_location = Column(Text)
    genes_file_sha256 = Column(Text)
    formatted_source_id = Column(Text)


class MetadataNucleotide(GtdbBase):
    __tablename__ = 'metadata_nucleotide'

    id = Column(ForeignKey('genomes.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    scaffold_count = Column(Integer)
    gc_count = Column(Integer)
    trna_aa_count = Column(Integer)
    longest_scaffold = Column(Integer)
    gc_percentage = Column(Float(53))
    total_gap_length = Column(Integer)
    genome_size = Column(Integer)
    n50_contigs = Column(Integer)
    n50_scaffolds = Column(Integer)
    l50_scaffolds = Column(Integer)
    contig_count = Column(Integer)
    ambiguous_bases = Column(Integer)
    longest_contig = Column(Integer)
    l50_contigs = Column(Integer)
    mean_scaffold_length = Column(Integer)
    mean_contig_length = Column(Integer)


class MetadataTaxonomy(GtdbBase):
    __tablename__ = 'metadata_taxonomy'

    id = Column(ForeignKey('genomes.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    # ncbi_type_strain = Column(Text)
    ncbi_taxonomy = Column(Text)
    gtdb_class = Column(Text)
    gtdb_species = Column(Text)
    gtdb_phylum = Column(Text)
    gtdb_family = Column(Text)
    gtdb_domain = Column(Text)
    gtdb_order = Column(Text)
    gtdb_genus = Column(Text)
    gtdb_genome_representative = Column(Text)
    gtdb_representative = Column(Boolean)
    ncbi_taxonomy_unfiltered = Column(Text)
    ncbi_type_material_designation = Column(Text)


class GtdbTaxonomyView(GtdbBase):
    __tablename__ = 'gtdb_taxonomy_mtview'

    id = Column(ForeignKey('genomes.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    gtdb_taxonomy = Column(Text)


class MetadataNcbi(GtdbBase):
    __tablename__ = 'metadata_ncbi'

    id = Column(ForeignKey('genomes.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    ncbi_biosample = Column(Text)
    ncbi_total_gap_length = Column(Integer)
    ncbi_molecule_count = Column(Integer)
    ncbi_date = Column(Text)
    ncbi_submitter = Column(Text)
    ncbi_ncrna_count = Column(Integer)
    ncbi_scaffold_n50 = Column(Integer)
    ncbi_assembly_name = Column(Text)
    ncbi_scaffold_n75 = Column(Integer)
    ncbi_protein_count = Column(Integer)
    ncbi_assembly_type = Column(Text)
    ncbi_rrna_count = Column(Integer)
    ncbi_genbank_assembly_accession = Column(Text)
    ncbi_total_length = Column(Integer)
    ncbi_unspanned_gaps = Column(Integer)
    ncbi_taxid = Column(Integer)
    ncbi_trna_count = Column(Integer)
    ncbi_genome_representation = Column(Text)
    ncbi_top_level_count = Column(Integer)
    ncbi_spanned_gaps = Column(Integer)
    ncbi_translation_table = Column(Integer)
    ncbi_scaffold_n90 = Column(Integer)
    ncbi_contig_count = Column(Integer)
    ncbi_organism_name = Column(Text)
    ncbi_region_count = Column(Integer)
    ncbi_contig_n50 = Column(Integer)
    ncbi_ungapped_length = Column(Integer)
    ncbi_scaffold_l50 = Column(Integer)
    ncbi_ssu_count = Column(Integer)
    ncbi_scaffold_count = Column(Integer)
    ncbi_assembly_level = Column(Text)
    ncbi_refseq_assembly_and_genbank_assemblies_identical = Column(Text)
    ncbi_release_type = Column(Text)
    ncbi_refseq_category = Column(Text)
    ncbi_species_taxid = Column(Text)
    ncbi_isolate = Column(Text)
    ncbi_version_status = Column(Text)
    ncbi_wgs_master = Column(Text)
    ncbi_asm_name = Column(Text)
    ncbi_bioproject = Column(Text)
    ncbi_paired_asm_comp = Column(Text)
    ncbi_seq_rel_date = Column(Text)
    ncbi_gbrs_paired_asm = Column(Text)
    ncbi_isolation_source = Column(Text)
    ncbi_country = Column(Text)
    ncbi_lat_lon = Column(Text)
    ncbi_strain_identifiers = Column(Text)
    ncbi_genome_category = Column(Text)
    ncbi_wgs_formatted = Column(Text)
    ncbi_cds_count = Column(Integer)


class MetadataGene(GtdbBase):
    __tablename__ = 'metadata_genes'

    id = Column(ForeignKey('genomes.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    checkm_completeness = Column(DOUBLE_PRECISION)
    checkm_contamination = Column(DOUBLE_PRECISION)
    protein_count = Column(Integer)
    coding_bases = Column(Integer)
    coding_density = Column(DOUBLE_PRECISION)
    ssu_count = Column(Integer)
    checkm_marker_count = Column(Integer)
    checkm_marker_lineage = Column(Text)
    checkm_genome_count = Column(Integer)
    checkm_marker_set_count = Column(Integer)
    checkm_strain_heterogeneity = Column(DOUBLE_PRECISION)
    lsu_23s_count = Column(Integer)
    lsu_5s_count = Column(Integer)
    checkm_strain_heterogeneity_100 = Column(DOUBLE_PRECISION)


class MetadataRna(GtdbBase):
    __tablename__ = 'metadata_rna'

    id = Column(ForeignKey('genomes.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    ssu_gg_taxonomy = Column(Text)
    ssu_gg_blast_bitscore = Column(Float(53))
    ssu_gg_blast_subject_id = Column(Text)
    ssu_gg_blast_perc_identity = Column(Float(53))
    ssu_gg_blast_evalue = Column(Float(53))
    ssu_gg_blast_align_len = Column(Float(53))
    ssu_gg_query_id = Column(Text)
    ssu_gg_length = Column(Integer)
    lsu_23s_contig_len = Column(Integer)
    ssu_contig_len = Column(Integer)
    lsu_silva_23s_blast_bitscore = Column(Float(53))
    lsu_silva_23s_taxonomy = Column(Text)
    lsu_silva_23s_blast_subject_id = Column(Text)
    lsu_23s_query_id = Column(Text)
    lsu_silva_23s_blast_align_len = Column(Integer)
    lsu_23s_length = Column(Integer)
    lsu_silva_23s_blast_evalue = Column(Float(53))
    lsu_silva_23s_blast_perc_identity = Column(Float(53))
    ssu_silva_blast_bitscore = Column(Float(53))
    ssu_silva_taxonomy = Column(Text)
    ssu_silva_blast_subject_id = Column(Text)
    ssu_query_id = Column(Text)
    ssu_silva_blast_align_len = Column(Integer)
    ssu_length = Column(Integer)
    ssu_silva_blast_evalue = Column(Float(53))
    ssu_silva_blast_perc_identity = Column(Float(53))
    lsu_5s_query_id = Column(Text)
    lsu_5s_length = Column(Integer)
    lsu_5s_contig_len = Column(Integer)


class MetadataTypeMaterial(GtdbBase):
    __tablename__ = 'metadata_type_material'

    id = Column(ForeignKey('genomes.id'), primary_key=True)
    gtdb_type_designation = Column(Text)
    gtdb_type_designation_sources = Column(Text)
    lpsn_type_designation = Column(Text)
    dsmz_type_designation = Column(Text)
    lpsn_priority_year = Column(Integer)
    gtdb_type_species_of_genus = Column(Boolean)


class GtdbTypeView(GtdbBase):
    __tablename__ = 'gtdb_type_view'

    id = Column(Integer, primary_key=True)
    gtdb_genus_type_species = Column(Boolean)
    gtdb_species_type_strain = Column(Boolean)


class LpsnGenera(GtdbBase):
    __tablename__ = 'lpsn_genera'

    lpsn_genus = Column(Text, primary_key=True)
    lpsn_type_genus = Column(Text)
    lpsn_genus_authority = Column(Text)


class LpsnSpecy(GtdbBase):
    __tablename__ = 'lpsn_species'

    lpsn_species = Column(Text, primary_key=True)
    lpsn_type_species = Column(Text)
    lpsn_species_authority = Column(Text)


class LpsnStrain(GtdbBase):
    __tablename__ = 'lpsn_strains'

    lpsn_strain = Column(Text, primary_key=True)


class UserRole(GtdbBase):
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)


class User(GtdbBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, server_default=text("nextval('users_id_seq'::regclass)"))
    username = Column(Text, nullable=False, unique=True)
    role_id = Column(ForeignKey('user_roles.id', onupdate='CASCADE'), nullable=False)
    has_root_login = Column(Boolean, nullable=False, server_default=text("false"))

    role = relationship('UserRole')


class MetadataView(GtdbBase):
    __tablename__ = 'metadata_view'

    id = Column(Integer, primary_key=True)
    accession = Column(Text)
    formatted_accession = Column(Text)
    organism_name = Column(Text)
    description = Column(Text)
    username = Column(Text)
    study_description = Column(Text)
    sequencing_platform = Column(Text)
    read_files = Column(Text)
    qc_program = Column(Text)
    assembly_program = Column(Text)
    gap_filling_program = Column(Text)
    mapping_program = Column(Text)
    binning_program = Column(Text)
    scaffolding_program = Column(Text)
    genome_assessment_program = Column(Text)
    refinement_description = Column(Text)
    scaffold_count = Column(Integer)
    gc_count = Column(Integer)
    longest_scaffold = Column(Integer)
    gc_percentage = Column(DOUBLE_PRECISION)
    total_gap_length = Column(Integer)
    genome_size = Column(Integer)
    n50_contigs = Column(Integer)
    n50_scaffolds = Column(Integer)
    l50_scaffolds = Column(Integer)
    contig_count = Column(Integer)
    ambiguous_bases = Column(Integer)
    longest_contig = Column(Integer)
    l50_contigs = Column(Integer)
    mean_scaffold_length = Column(Integer)
    mean_contig_length = Column(Integer)
    trna_aa_count = Column(Integer)
    trna_selenocysteine_count = Column(Integer)
    trna_count = Column(Integer)
    checkm_completeness = Column(DOUBLE_PRECISION)
    checkm_contamination = Column(DOUBLE_PRECISION)
    protein_count = Column(Integer)
    coding_bases = Column(Integer)
    coding_density = Column(DOUBLE_PRECISION)
    ssu_count = Column(Integer)
    checkm_marker_count = Column(Integer)
    checkm_marker_lineage = Column(Integer)
    checkm_genome_count = Column(Integer)
    checkm_marker_set_count = Column(Integer)
    checkm_strain_heterogeneity = Column(DOUBLE_PRECISION)
    lsu_23s_count = Column(Integer)
    lsu_5s_count = Column(Integer)
    checkm_strain_heterogeneity_100 = Column(DOUBLE_PRECISION)
    ncbi_taxonomy = Column(Text)
    gtdb_class = Column(Text)
    gtdb_species = Column(Text)
    gtdb_phylum = Column(Text)
    gtdb_family = Column(Text)
    gtdb_domain = Column(Text)
    gtdb_order = Column(Text)
    gtdb_genus = Column(Text)
    gtdb_genome_representative = Column(Text)
    gtdb_representative = Column(Boolean)
    ncbi_taxonomy_unfiltered = Column(Text)
    ncbi_type_material_designation = Column(Text)
    ncbi_biosample = Column(Text)
    ncbi_total_gap_length = Column(Integer)
    ncbi_molecule_count = Column(Integer)
    ncbi_date = Column(Text)
    ncbi_submitter = Column(Text)
    ncbi_ncrna_count = Column(Integer)
    ncbi_scaffold_n50 = Column(Integer)
    ncbi_assembly_name = Column(Text)
    ncbi_scaffold_n75 = Column(Integer)
    ncbi_protein_count = Column(Integer)
    ncbi_assembly_type = Column(Text)
    ncbi_rrna_count = Column(Integer)
    ncbi_genbank_assembly_accession = Column(Text)
    ncbi_total_length = Column(Integer)
    ncbi_unspanned_gaps = Column(Integer)
    ncbi_taxid = Column(Integer)
    ncbi_trna_count = Column(Integer)
    ncbi_genome_representation = Column(Text)
    ncbi_top_level_count = Column(Integer)
    ncbi_spanned_gaps = Column(Integer)
    ncbi_translation_table = Column(Integer)
    ncbi_scaffold_n90 = Column(Integer)
    ncbi_contig_count = Column(Integer)
    ncbi_organism_name = Column(Text)
    ncbi_region_count = Column(Integer)
    ncbi_contig_n50 = Column(Integer)
    ncbi_ungapped_length = Column(Integer)
    ncbi_scaffold_l50 = Column(Integer)
    ncbi_ssu_count = Column(Integer)
    ncbi_scaffold_count = Column(Integer)
    ncbi_assembly_level = Column(Text)
    ncbi_refseq_assembly_and_genbank_assemblies_identical = Column(Text)
    ncbi_release_type = Column(Text)
    ncbi_refseq_category = Column(Text)
    ncbi_species_taxid = Column(Text)
    ncbi_isolate = Column(Text)
    ncbi_version_status = Column(Text)
    ncbi_wgs_master = Column(Text)
    ncbi_asm_name = Column(Text)
    ncbi_bioproject = Column(Text)
    ncbi_paired_asm_comp = Column(Text)
    ncbi_seq_rel_date = Column(Text)
    ncbi_gbrs_paired_asm = Column(Text)
    ncbi_isolation_source = Column(Text)
    ncbi_country = Column(Text)
    ncbi_lat_lon = Column(Text)
    ncbi_strain_identifiers = Column(Text)
    ncbi_genome_category = Column(Text)
    ncbi_wgs_formatted = Column(Text)
    ncbi_cds_count = Column(Integer)
    ssu_gg_taxonomy = Column(Text)
    ssu_gg_blast_bitscore = Column(DOUBLE_PRECISION)
    ssu_gg_blast_subject_id = Column(Text)
    ssu_gg_blast_perc_identity = Column(DOUBLE_PRECISION)
    ssu_gg_blast_evalue = Column(DOUBLE_PRECISION)
    ssu_gg_blast_align_len = Column(Integer)
    ssu_gg_query_id = Column(Text)
    ssu_gg_length = Column(Integer)
    lsu_23s_contig_len = Column(Integer)
    ssu_contig_len = Column(Integer)
    lsu_silva_23s_blast_bitscore = Column(DOUBLE_PRECISION)
    lsu_silva_23s_taxonomy = Column(Text)
    lsu_silva_23s_blast_subject_id = Column(Text)
    lsu_23s_query_id = Column(Text)
    lsu_silva_23s_blast_align_len = Column(Integer)
    lsu_23s_length = Column(Integer)
    lsu_silva_23s_blast_evalue = Column(DOUBLE_PRECISION)
    lsu_silva_23s_blast_perc_identity = Column(DOUBLE_PRECISION)
    ssu_silva_blast_bitscore = Column(DOUBLE_PRECISION)
    ssu_silva_taxonomy = Column(Text)
    ssu_silva_blast_subject_id = Column(Text)
    ssu_query_id = Column(Text)
    ssu_silva_blast_align_len = Column(Integer)
    ssu_length = Column(Integer)
    ssu_silva_blast_evalue = Column(DOUBLE_PRECISION)
    ssu_silva_blast_perc_identity = Column(DOUBLE_PRECISION)
    lsu_5s_query_id = Column(Text)
    lsu_5s_length = Column(Integer)
    lsu_5s_contig_len = Column(Integer)
    gtdb_taxonomy = Column(Text)
    mimag_high_quality = Column(Boolean)
    mimag_medium_quality = Column(Boolean)
    mimag_low_quality = Column(Boolean)
    gtdb_genus_type_species = Column(Boolean)
    gtdb_species_type_strain = Column(Boolean)
    gtdb_cluster_size = Column(BIGINT)
    gtdb_clustered_genomes = Column(Text)
    gtdb_type_designation = Column(Text)
    gtdb_type_designation_sources = Column(Text)
    lpsn_type_designation = Column(Text)
    dsmz_type_designation = Column(Text)
    lpsn_priority_year = Column(Integer)
    gtdb_type_species_of_genus = Column(Boolean)


class GenomeLists(GtdbBase):  # OK
    __tablename__ = 'genome_lists'

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    description = Column(Text)
    owned_by_root = Column(Boolean)
    owner_id = Column(ForeignKey('users.id'))
    private = Column(Boolean)
    display_order = Column(Integer)


class GenomeListContents(GtdbBase):  # OK
    __tablename__ = 'genome_list_contents'

    list_id = Column(ForeignKey('genome_lists.id'), primary_key=True)
    genome_id = Column(ForeignKey('genomes.id'), primary_key=True)


class UBAView(GtdbBase):
    __tablename__ = 'uba_mtview'

    id = Column(ForeignKey('genomes.id'), primary_key=True)
    uba_number = Column(Text)


class SurveyGenomes(GtdbBase):
    __tablename__ = 'survey_genomes'

    canonical_gid = Column(CHAR(length=20), primary_key=True)


# Manually done below

class GtdbSpeciesClusterCount(GtdbBase):
    __tablename__ = 'gtdb_species_cluster_count'

    column_not_exist_in_db = Column(Integer, primary_key=True)

    gtdb_domain = Column(Text)
    gtdb_phylum = Column(Text)
    gtdb_class = Column(Text)
    gtdb_order = Column(Text)
    gtdb_family = Column(Text)
    gtdb_genus = Column(Text)
    gtdb_species = Column(Text)
    cnt = Column(Integer)


# gtdb web

class DbGtdbTree(GtdbWebBase):
    __tablename__ = 'gtdb_tree'

    id = Column(Integer, primary_key=True)
    taxon = Column(Text)
    total = Column(Integer)
    type = Column(Text)
    is_rep = Column(Boolean)
    type_material = Column(Text)
    n_desc_children = Column(Integer)
    bergeys_url = Column(Text)


class DbGtdbTreeChildren(GtdbWebBase):
    __tablename__ = 'gtdb_tree_children'

    parent_id = Column(ForeignKey(DbGtdbTree.id), primary_key=True)
    child_id = Column(ForeignKey(DbGtdbTree.id), primary_key=True)
    order_id = Column(Integer)


class GtdbSearchMtView(GtdbBase):
    """This is a materialized view."""
    __tablename__ = 'gtdb_search_mtview'

    column_not_exist_in_db = Column(Integer, primary_key=True)

    id_at_source = Column(Text)
    ncbi_organism_name = Column(Text)
    ncbi_taxonomy = Column(Text)
    gtdb_taxonomy = Column(Text)
    ncbi_genbank_assembly_accession = Column(Text)
    ncbi_type_material_designation = Column(Text)
    gtdb_representative = Column(Boolean)
    formatted_source_id = Column(Text)


class GtdbWebTaxonHist(GtdbWebBase):
    __tablename__ = 'taxon_hist'
    release_ver = Column(Text, primary_key=True)
    genome_id = Column(Text, primary_key=True)
    rank_domain = Column(Text)
    rank_phylum = Column(Text)
    rank_class = Column(Text)
    rank_order = Column(Text)
    rank_family = Column(Text)
    rank_genus = Column(Text)
    rank_species = Column(Text)


class GtdbWebLpsnUrl(GtdbWebBase):
    __tablename__ = 'lpsn_url'
    gtdb_species = Column(Text, primary_key=True)
    lpsn_url = Column(Text)


class GtdbWebGenomeTaxId(GtdbWebBase):
    __tablename__ = 'genome_taxid'
    genome_id = Column(Text, primary_key=True)
    payload = Column(JSON)


class GtdbWebTaxaNotInLit(GtdbWebBase):
    __tablename__ = 'gtdb_taxa_not_in_lit'
    taxon = Column(Text, primary_key=True)
    gtdb_domain = Column(Text)
    gtdb_phylum = Column(Text)
    gtdb_class = Column(Text)
    gtdb_order = Column(Text)
    gtdb_family = Column(Text)
    gtdb_genus = Column(Text)
    gtdb_species = Column(Text)
    appeared_in_release = Column(Text)
    taxon_status = Column(Text)
    notes = Column(Text)


class GtdbWebUbaAlias(GtdbWebBase):
    __tablename__ = 'uba_alias'
    id = Column(Integer, primary_key=True)
    u_accession = Column(Text, nullable=False)
    uba_accession = Column(Text, nullable=False)
    ncbi_accession = Column(Text)

# class GtdbWebSpeciesHeatmap(GtdbWebBase):
#     __tablename__ = 'species_heatmap'
#     species = Column(Text, primary_key=True)
#     gid = Column(Text, primary_key=True)
#     x_order = Column(Integer)
#     y_order = Column(Integer)
#
#
# class GtdbWebAni(GtdbWebBase):
#     __tablename__ = 'ani'
#     q = Column(Text, primary_key=True)
#     r = Column(Text, primary_key=True)
#     ani = Column(Float)
#     n_frag = Column(Integer)
#     n_total_frag = Column(Integer)
