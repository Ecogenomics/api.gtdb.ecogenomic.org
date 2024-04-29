import datetime

from sqlalchemy import CHAR, Boolean, Column, Date, DateTime, Float, \
    ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, BIGINT
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP
from sqlalchemy.orm import relationship

from api.db import GtdbBase, GtdbWebBase, GtdbCommonBase, GtdbFastaniBase


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

    id = Column(ForeignKey('genomes.id'), primary_key=True)
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
    checkm2_completeness = Column(DOUBLE_PRECISION)
    checkm2_contamination = Column(DOUBLE_PRECISION)
    checkm2_model = Column(Text)


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
    gtdb_type_designation_ncbi_taxa = Column(Text)
    gtdb_type_designation_ncbi_taxa_sources = Column(Text)
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
    __tablename__ = 'metadata_mtview'

    id = Column(Integer, primary_key=True)
    accession = Column(Text)
    formatted_accession = Column(Text)
    organism_name = Column(Text)
    description = Column(Text)
    username = Column(Text)
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
    checkm2_completeness = Column(DOUBLE_PRECISION)
    checkm2_contamination = Column(DOUBLE_PRECISION)
    checkm2_model = Column(Text)
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
    ncbi_untrustworthy_as_type = Column(Boolean)
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
    seqcode_id = Column(Integer)
    seqcode_name = Column(Text)
    seqcode_rank = Column(Text)
    seqcode_species_status = Column(Text)
    seqcode_genus_status = Column(Text)
    seqcode_family_status = Column(Text)
    seqcode_order_status = Column(Text)
    seqcode_class_status = Column(Text)
    seqcode_phylum_status = Column(Text)
    seqcode_type_species_of_genus = Column(Boolean)
    seqcode_type_genus_of_family = Column(Boolean)
    seqcode_type_family_of_order = Column(Boolean)
    seqcode_type_order_of_class = Column(Boolean)
    seqcode_type_class_of_phylum = Column(Boolean)
    seqcode_classification = Column(Text)
    seqcode_proposed_by = Column(Text)
    seqcode_created_at = Column(Text)
    seqcode_updated_at = Column(Text)
    seqcode_url = Column(Text)
    seqcode_priority_date = Column(Text)
    gtdb_taxonomy = Column(Text)
    mimag_high_quality = Column(Boolean)
    mimag_medium_quality = Column(Boolean)
    mimag_low_quality = Column(Boolean)
    gtdb_genus_type_species = Column(Boolean)
    gtdb_species_type_strain = Column(Boolean)
    gtdb_cluster_size = Column(BIGINT)
    gtdb_clustered_genomes = Column(Text)
    gtdb_type_designation_ncbi_taxa = Column(Text)
    gtdb_type_designation_ncbi_taxa_sources = Column(Text)
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


class GtdbWebUrlBergeys(GtdbWebBase):
    __tablename__ = 'gtdb_tree_url_bergeys'
    id = Column(ForeignKey(DbGtdbTree.id), primary_key=True, nullable=False)
    url = Column(Text, nullable=False)


class GtdbWebUrlLpsn(GtdbWebBase):
    __tablename__ = 'gtdb_tree_url_lpsn'
    id = Column(ForeignKey(DbGtdbTree.id), primary_key=True, nullable=False)
    url = Column(Text, nullable=False)


class GtdbWebUrlNcbi(GtdbWebBase):
    __tablename__ = 'gtdb_tree_url_ncbi'
    id = Column(ForeignKey(DbGtdbTree.id), primary_key=True, nullable=False)
    taxid = Column(Integer, nullable=False)


class GtdbWebUrlSeqcode(GtdbWebBase):
    __tablename__ = 'gtdb_tree_url_seqcode'
    id = Column(ForeignKey(DbGtdbTree.id), primary_key=True, nullable=False)
    url = Column(Text, nullable=False)


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


class GtdbCommonGenomes(GtdbCommonBase):
    __tablename__ = 'genomes'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    fna_gz_md5 = Column(Text)
    assembly_url = Column(Text)


class GtdbCommonLpsnHtml(GtdbCommonBase):
    __tablename__ = 'lpsn_html'
    id = Column(Integer, primary_key=True)
    url = Column(Text, nullable=False)
    created = Column(TIMESTAMP, nullable=False)
    updated = Column(TIMESTAMP, nullable=False)
    html = Column(Text, nullable=True)
    to_process = Column(Boolean, nullable=False, default=True)

    # Output columns
    name = Column(Text, nullable=True)
    category = Column(Text, nullable=True)
    proposed_as = Column(Text, nullable=True)
    etymology = Column(Text, nullable=True)
    original_publication = Column(Text, nullable=True)
    original_publication_doi = Column(Text, nullable=True)
    nomenclatural_status = Column(Text, nullable=True)
    n_child_correct = Column(Integer, nullable=True)
    n_child_synonym = Column(Integer, nullable=True)
    n_child_total = Column(Integer, nullable=True)
    parent_taxon = Column(ForeignKey('lpsn_html.id'), nullable=True)
    assigned_by = Column(Text, nullable=True)
    assigned_by_doi = Column(Text, nullable=True)
    record_number = Column(Integer, nullable=True)
    type_genus = Column(ForeignKey('lpsn_html.id'), nullable=True)
    gender = Column(Text, nullable=True)
    valid_publication = Column(Text, nullable=True)
    valid_publication_doi = Column(Text, nullable=True)
    ijsem_list = Column(Text, nullable=True)
    ijsem_list_doi = Column(Text, nullable=True)
    taxonomic_status = Column(Text, nullable=True)
    type_order = Column(ForeignKey('lpsn_html.id'), nullable=True)
    type_class = Column(ForeignKey('lpsn_html.id'), nullable=True)
    effective_publication = Column(Text, nullable=True)
    effective_publication_doi = Column(Text, nullable=True)
    emendations = Column(Text, nullable=True)
    type_subgenus = Column(ForeignKey('lpsn_html.id'), nullable=True)
    type_species = Column(ForeignKey('lpsn_html.id'), nullable=True)
    tygs = Column(Text, nullable=True)
    type_strain = Column(Text, nullable=True)
    ssu_ggdc = Column(Text, nullable=True)
    ssu_fasta = Column(Text, nullable=True)
    ssu_ebi = Column(Text, nullable=True)
    ssu_ncbi = Column(Text, nullable=True)
    ssu = Column(Text, nullable=True)
    strain_info = Column(Text, nullable=True)
    risk_group = Column(Integer, nullable=True)
    basonym = Column(ForeignKey('lpsn_html.id'), nullable=True)


class GtdbCommonLpsnHtmlNotes(GtdbCommonBase):
    __tablename__ = 'lpsn_html_notes'
    id = Column(Integer, primary_key=True)
    page_id = Column(ForeignKey('lpsn_html.id'), nullable=False)
    doi = Column(Text, nullable=True)
    note = Column(Text, nullable=True)


class GtdbCommonLpsnHtmlChildTaxa(GtdbCommonBase):
    __tablename__ = 'lpsn_html_child_taxa'
    id = Column(Integer, primary_key=True)
    parent_page_id = Column(ForeignKey('lpsn_html.id'), nullable=False)
    child_page_id = Column(ForeignKey('lpsn_html.id'), nullable=False)
    nomenclatural_status = Column(Text, nullable=True)
    taxonomic_status = Column(Text, nullable=True)


class GtdbCommonLpsnHtmlSynonyms(GtdbCommonBase):
    __tablename__ = 'lpsn_html_synonyms'
    id = Column(Integer, primary_key=True)
    page_id = Column(ForeignKey('lpsn_html.id'), nullable=False)
    synonym_id = Column(ForeignKey('lpsn_html.id'), nullable=False)
    kind = Column(Text, nullable=False)


class GtdbCommonSeqCodeHtml(GtdbCommonBase):
    __tablename__ = 'seqcode_html'
    id = Column(Integer, primary_key=True)
    updated = Column(TIMESTAMP, nullable=False, default=datetime.datetime.utcnow)
    to_process = Column(Boolean, nullable=False)
    etag = Column(Text, nullable=True)
    name = Column(Text, nullable=True)
    rank = Column(Text, nullable=True)
    status_name = Column(Text, nullable=True)
    syllabification = Column(Text, nullable=True)
    priority_date = Column(TIMESTAMP, nullable=True)
    formal_styling_raw = Column(Text, nullable=True)
    formal_styling_html = Column(Text, nullable=True)
    etymology = Column(Text, nullable=True)
    sc_created_at = Column(TIMESTAMP, nullable=True)
    sc_updated_at = Column(TIMESTAMP, nullable=True)
    domain_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    phylum_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    class_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    order_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    family_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    genus_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    species_id = Column(ForeignKey('seqcode_html.id'), nullable=True)
    corrigendum_by_id = Column(Integer, nullable=True)
    corrigendum_by_citation = Column(Text, nullable=True)
    corrigendum_from = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    description_raw = Column(Text, nullable=True)
    proposed_by_id = Column(Text, nullable=True)
    proposed_by_citation = Column(Text, nullable=True)
    notes_raw = Column(Text, nullable=True)
    notes_html = Column(Text, nullable=True)


class GtdbCommonSeqCodeHtmlChildren(GtdbCommonBase):
    __tablename__ = 'seqcode_html_children'
    parent_id = Column(Integer, primary_key=True)
    child_id = Column(Integer, primary_key=True)


class GtdbCommonSeqCodeHtmlQcWarnings(GtdbCommonBase):
    __tablename__ = 'seqcode_html_qc_warnings'
    id = Column(Integer, primary_key=True)
    sc_id = Column(ForeignKey('seqcode_html.id'), nullable=False)
    can_approve = Column(Boolean, nullable=True)
    text = Column(Text, nullable=False)
    rules = Column(Text, nullable=True)


class GtdbCommonNcbiCitation(GtdbCommonBase):
    __tablename__ = 'ncbi_citation'
    cit_id = Column(Integer, primary_key=True)
    cit_key = Column(Text)
    pubmed_id = Column(Integer)
    medline_id = Column(Integer)
    url = Column(Text)
    content = Column(Text)


class GtdbCommonNcbiDivision(GtdbCommonBase):
    __tablename__ = 'ncbi_division'
    division_id = Column(Integer, primary_key=True)
    cde = Column(Text)
    name = Column(Text)
    comments = Column(Text)


class GtdbCommonNcbiGencode(GtdbCommonBase):
    __tablename__ = 'ncbi_gencode'
    gencode_id = Column(Integer, primary_key=True)
    abbreviation = Column(Text)
    name = Column(Text)
    cde = Column(Text)
    starts = Column(Text)


class GtdbCommonNcbiMergedNode(GtdbCommonBase):
    __tablename__ = 'ncbi_merged_node'
    old_tax_id = Column(ForeignKey('ncbi_node.tax_id'), primary_key=True)
    new_tax_id = Column(ForeignKey('ncbi_node.tax_id'), primary_key=True)


class GtdbCommonNcbiName(GtdbCommonBase):
    __tablename__ = 'ncbi_name'

    column_not_exist_in_db = Column(Integer, primary_key=True)

    tax_id = Column(ForeignKey('ncbi_node.tax_id'))
    name_txt = Column(Text)
    unique_name = Column(Text)
    name_class = Column(Text)


class GtdbCommonNcbiNode(GtdbCommonBase):
    __tablename__ = 'ncbi_node'
    tax_id = Column(Integer, primary_key=True)
    parent_tax_id = Column(ForeignKey('ncbi_node.tax_id'))
    rank = Column(Text)
    embl_code = Column(Text)
    division_id = Column(ForeignKey('ncbi_division.division_id'))
    inherited_div_flag = Column(Boolean)
    gencode_id = Column(ForeignKey('ncbi_gencode.gencode_id'))
    inherited_gc_flag = Column(Boolean)
    mito_gencode_id = Column(ForeignKey('ncbi_gencode.gencode_id'))
    inherited_mgc_flag = Column(Boolean)
    genbank_hidden = Column(Boolean)
    hidden_subtree_root = Column(Boolean)
    comments = Column(Text)
    is_deleted = Column(Boolean)


class GtdbCommonNcbiNodeCitation(GtdbCommonBase):
    __tablename__ = 'ncbi_node_citation'
    tax_id = Column(ForeignKey('ncbi_node.tax_id'), primary_key=True)
    cit_id = Column(ForeignKey('ncbi_citation.cit_id'), primary_key=True)


class GtdbCommonBergeysHtml(GtdbCommonBase):
    __tablename__ = 'bergeys_html'
    page_id = Column(Integer, primary_key=True, nullable=False)
    updated = Column(TIMESTAMP, nullable=False)
    html = Column(Text, nullable=False)


class GtdbCommonBergeysTaxa(GtdbCommonBase):
    __tablename__ = 'bergeys_taxa'
    taxon_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    content = Column(Text)


class GtdbCommonBergeysTaxaChildren(GtdbCommonBase):
    __tablename__ = 'bergeys_taxa_children'
    parent_id = Column(ForeignKey('bergeys_taxa.taxon_id'), primary_key=True, nullable=False)
    child_id = Column(ForeignKey('bergeys_taxa.taxon_id'), primary_key=True, nullable=False)


class GtdbFastaniGenome(GtdbFastaniBase):
    __tablename__ = 'genome'
    id = Column(Integer, primary_key=True)
    name = Column(CHAR(15), nullable=False)
    fna_gz_md5 = Column(CHAR(32), nullable=False)
    assembly_url = Column(Text, nullable=True)


class GtdbFastaniJob(GtdbFastaniBase):
    __tablename__ = 'job'
    id = Column(Integer, primary_key=True)
    created = Column(TIMESTAMP, nullable=False)
    email = Column(Text, nullable=True)
    param_id = Column(ForeignKey('param.id'), nullable=False)


class GtdbFastaniJobResult(GtdbFastaniBase):
    __tablename__ = 'job_result'
    job_id = Column(ForeignKey('job.id'), primary_key=True, nullable=False)
    result_id = Column(ForeignKey('result.id'), primary_key=True, nullable=False)


class GtdbFastaniParam(GtdbFastaniBase):
    __tablename__ = 'param'
    id = Column(Integer, primary_key=True)
    version = Column(ForeignKey('version.id'), primary_key=False, nullable=False)
    frag_len = Column(Integer, nullable=False)
    kmer_size = Column(Integer, nullable=False)
    min_align_frac = Column(Float, nullable=True)
    min_align_frag = Column(Integer, nullable=True)


class GtdbFastaniQueue(GtdbFastaniBase):
    __tablename__ = 'queue'
    result_id = Column(ForeignKey('result.id'), primary_key=True, nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)


class GtdbFastaniResult(GtdbFastaniBase):
    __tablename__ = 'result'
    id = Column(Integer, primary_key=True)
    qry_id = Column(ForeignKey('genome.id'), primary_key=False, nullable=False)
    ref_id = Column(ForeignKey('genome.id'), primary_key=False, nullable=False)
    param_id = Column(ForeignKey('param.id'), primary_key=False, nullable=False)
    ani = Column(Float, nullable=True)
    mapped_frag = Column(Integer, nullable=True)
    total_frag = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    completed = Column(Boolean, nullable=False)
    priority = Column(Integer, nullable=False)
    error = Column(Boolean, nullable=False)


class GtdbFastaniVersion(GtdbFastaniBase):
    __tablename__ = 'version'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)


class GtdbFastaniJobQuery(GtdbFastaniBase):
    __tablename__ = 'job_query'
    job_id = Column(ForeignKey('job.id'), primary_key=True, nullable=False)
    genome_id = Column(ForeignKey('genome.id'), primary_key=True, nullable=False)


class GtdbFastaniJobReference(GtdbFastaniBase):
    __tablename__ = 'job_reference'
    job_id = Column(ForeignKey('job.id'), primary_key=True, nullable=False)
    genome_id = Column(ForeignKey('genome.id'), primary_key=True, nullable=False)
