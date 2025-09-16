from datetime import datetime, date

from sqlmodel import Field, SQLModel, Column, TIMESTAMP, Date, CHAR

"""
Tables below.
"""


class DbAlignedMarkers(SQLModel, table=True):
    __tablename__ = 'aligned_markers'

    id: int | None = Field(primary_key=True, default=None, foreign_key="genome.id")
    marker_id: int = Field(primary_key=True, foreign_key="markers.id")
    sequence: str | None = Field(default=None)
    multiple_hits: bool = Field()
    evalue: str | None = Field(default=None)
    bitscore: str | None = Field(default=None)
    hit_number: int | None = Field(default=None)
    unique_genes: int | None = Field(default=None)


class DbGenomeListContents(SQLModel, table=True):
    __tablename__ = 'genome_list_contents'

    list_id: int | None = Field(primary_key=True, default=None, foreign_key="genome_lists.id")
    genome_id: int | None = Field(primary_key=True, default=None, foreign_key="genomes.id")


class DbGenomeLists(SQLModel, table=True):
    __tablename__ = 'genome_lists'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field()
    description: str | None = Field(default=None)
    owned_by_root: bool = Field(default=False)
    owner_id: int | None = Field(foreign_key="users.id")
    private: bool | None = Field(default=True)
    display_order: int | None = Field(default=1000)


class DbGenomeSources(SQLModel, table=True):
    __tablename__ = 'genome_sources'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(unique=True)
    external_id_prefix: str = Field(unique=True)
    last_auto_id: int = Field(default=0)
    user_editable: int = Field(default=False)


class DbGenomes(SQLModel, table=True):  # OK
    __tablename__ = 'genomes'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field()
    description: str | None = Field(None)
    owned_by_root: bool = Field(default=False)
    owner_id: int | None = Field(foreign_key="users.id", default=None)
    fasta_file_location: str = Field()
    fasta_file_sha256: str = Field()
    genome_source_id: int = Field(foreign_key='genome_sources.id')
    id_at_source: str = Field()
    date_added: datetime = Field(sa_column=Column(TIMESTAMP()))
    has_changed: bool = Field(default=True)
    last_update: date | None = Field(sa_column=Column(Date), default=None)
    genes_file_location: str | None = Field(default=None)
    genes_file_sha256: str | None = Field(default=None)
    formatted_source_id: str | None = Field(default=None)


class DbMarkerDatabases(SQLModel, table=True):
    __tablename__ = 'marker_databases'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field()
    external_id_prefix: str = Field()
    last_auto_id: int = Field(default=0)
    user_editable: bool = Field(default=False)


class DbMarkerSetContents(SQLModel, table=True):
    __tablename__ = 'marker_set_contents'

    set_id: int = Field(primary_key=True, foreign_key="marker_sets.id")
    marker_id: int = Field(primary_key=True, foreign_key="markers.id")


class DbMarkerSets(SQLModel, table=True):
    __tablename__ = 'marker_sets'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field()
    description: str | None = Field(default=None)
    owned_by_root: bool = Field(default=False)
    owner_id: int | None = Field(foreign_key="users.id", default=None)
    private: bool | None = Field(default=True)


class DbMarkers(SQLModel, table=True):
    __tablename__ = 'markers'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field()
    description: str | None = Field(default=None)
    owned_by_root: bool = Field(default=False)
    owner_id: int | None = Field(default=None)
    marker_file_location: str = Field()
    marker_file_sha256: str = Field()
    marker_database_id: int = Field(foreign_key="marker_databases.id")
    id_in_database: str = Field()
    size: int = Field()


class DbMetadataGenes(SQLModel, table=True):
    __tablename__ = 'metadata_genes'

    id: int | None = Field(primary_key=True, default=None, foreign_key="genomes.id")
    checkm_completeness: float | None = Field(default=None)
    checkm_contamination: float | None = Field(default=None)
    protein_count: int | None = Field(default=None)
    coding_bases: int | None = Field(default=None)
    coding_density: float | None = Field(default=None)
    ssu_count: int | None = Field(default=None)
    checkm_marker_count: int | None = Field(default=None)
    checkm_marker_lineage: str | None = Field(default=None)
    checkm_genome_count: int | None = Field(default=None)
    checkm_marker_set_count: int | None = Field(default=None)
    checkm_strain_heterogeneity: float | None = Field(default=None)
    lsu_23s_count: int | None = Field(default=None)
    lsu_5s_count: int | None = Field(default=None)
    checkm_strain_heterogeneity_100: float | None = Field(default=None)
    checkm2_completeness: float | None = Field(default=None)
    checkm2_contamination: float | None = Field(default=None)
    checkm2_model: str | None = Field(default=None)


class DbMetadataNcbi(SQLModel, table=True):
    __tablename__ = 'metadata_ncbi'

    id: int | None = Field(primary_key=True, default=None, foreign_key="genomes.id")
    ncbi_biosample: str | None = Field(default=None)
    ncbi_total_gap_length: int | None = Field(default=None)
    ncbi_molecule_count: int | None = Field(default=None)
    ncbi_date: str | None = Field(default=None)
    ncbi_submitter: str | None = Field(default=None)
    ncbi_ncrna_count: int | None = Field(default=None)
    ncbi_scaffold_n50: int | None = Field(default=None)
    ncbi_assembly_name: str | None = Field(default=None)
    ncbi_scaffold_n75: int | None = Field(default=None)
    ncbi_protein_count: int | None = Field(default=None)
    ncbi_assembly_type: str | None = Field(default=None)
    ncbi_rrna_count: int | None = Field(default=None)
    ncbi_genbank_assembly_accession: str | None = Field(default=None)
    ncbi_total_length: int | None = Field(default=None)
    ncbi_unspanned_gaps: int | None = Field(default=None)
    ncbi_taxid: int | None = Field(default=None)
    ncbi_trna_count: int | None = Field(default=None)
    ncbi_genome_representation: str | None = Field(default=None)
    ncbi_top_level_count: int | None = Field(default=None)
    ncbi_spanned_gaps: int | None = Field(default=None)
    ncbi_translation_table: int | None = Field(default=None)
    ncbi_scaffold_n90: int | None = Field(default=None)
    ncbi_contig_count: int | None = Field(default=None)
    ncbi_organism_name: str | None = Field(default=None)
    ncbi_region_count: int | None = Field(default=None)
    ncbi_contig_n50: int | None = Field(default=None)
    ncbi_ungapped_length: int | None = Field(default=None)
    ncbi_scaffold_l50: int | None = Field(default=None)
    ncbi_ssu_count: int | None = Field(default=None)
    ncbi_scaffold_count: int | None = Field(default=None)
    ncbi_assembly_level: str | None = Field(default=None)
    ncbi_refseq_assembly_and_genbank_assemblies_identical: str | None
    ncbi_release_type: str | None = Field(default=None)
    ncbi_refseq_category: str | None = Field(default=None)
    ncbi_species_taxid: str | None = Field(default=None)
    ncbi_isolate: str | None = Field(default=None)
    ncbi_version_status: str | None = Field(default=None)
    ncbi_wgs_master: str | None = Field(default=None)
    ncbi_asm_name: str | None = Field(default=None)
    ncbi_bioproject: str | None = Field(default=None)
    ncbi_paired_asm_comp: str | None = Field(default=None)
    ncbi_seq_rel_date: str | None = Field(default=None)
    ncbi_gbrs_paired_asm: str | None = Field(default=None)
    ncbi_isolation_source: str | None = Field(default=None)
    ncbi_country: str | None = Field(default=None)
    ncbi_lat_lon: str | None = Field(default=None)
    ncbi_strain_identifiers: str | None = Field(default=None)
    ncbi_genome_category: str | None = Field(default=None)
    ncbi_wgs_formatted: str | None = Field(default=None)
    ncbi_cds_count: int | None = Field(default=None)
    ncbi_not_used_as_type: bool | None = Field(default=None)
    ncbi_excluded_from_refseq: bool | None = Field(default=None)


class DbMetadataNucleotide(SQLModel, table=True):
    __tablename__ = 'metadata_nucleotide'

    id: int | None = Field(primary_key=True, default=None, foreign_key="genomes.id")
    scaffold_count: int | None = Field(default=None)
    gc_count: int | None = Field(default=None)
    longest_scaffold: int | None = Field(default=None)
    gc_percentage: float | None = Field(default=None)
    total_gap_length: int | None = Field(default=None)
    genome_size: int | None = Field(default=None)
    n50_contigs: int | None = Field(default=None)
    n50_scaffolds: int | None = Field(default=None)
    l50_scaffolds: int | None = Field(default=None)
    contig_count: int | None = Field(default=None)
    ambiguous_bases: int | None = Field(default=None)
    longest_contig: int | None = Field(default=None)
    l50_contigs: int | None = Field(default=None)
    mean_scaffold_length: int | None = Field(default=None)
    mean_contig_length: int | None = Field(default=None)
    trna_aa_count: int | None = Field(default=None)
    trna_selenocysteine_count: int | None = Field(default=None)
    trna_count: int | None = Field(default=None)


class DbMetadataRna(SQLModel, table=True):
    __tablename__ = 'metadata_rna'

    id: int | None = Field(primary_key=True, default=None, foreign_key="genomes.id")
    ssu_gg_taxonomy: str | None = Field(default=None)
    ssu_gg_blast_bitscore: float | None = Field(default=None)
    ssu_gg_blast_subject_id: str | None = Field(default=None)
    ssu_gg_blast_perc_identity: float | None = Field(default=None)
    ssu_gg_blast_evalue: float | None = Field(default=None)
    ssu_gg_blast_align_len: float | None = Field(default=None)
    ssu_gg_query_id: str | None = Field(default=None)
    ssu_gg_length: int | None = Field(default=None)
    lsu_23s_contig_len: int | None = Field(default=None)
    ssu_contig_len: int | None = Field(default=None)
    lsu_silva_23s_blast_bitscore: float | None = Field(default=None)
    lsu_silva_23s_taxonomy: str | None = Field(default=None)
    lsu_silva_23s_blast_subject_id: str | None = Field(default=None)
    lsu_23s_query_id: str | None = Field(default=None)
    lsu_silva_23s_blast_align_len: int | None = Field(default=None)
    lsu_23s_length: int | None = Field(default=None)
    lsu_silva_23s_blast_evalue: float | None = Field(default=None)
    lsu_silva_23s_blast_perc_identity: float | None = Field(default=None)
    ssu_silva_blast_bitscore: float | None = Field(default=None)
    ssu_silva_taxonomy: str | None = Field(default=None)
    ssu_silva_blast_subject_id: str | None = Field(default=None)
    ssu_query_id: str | None = Field(default=None)
    ssu_silva_blast_align_len: int | None = Field(default=None)
    ssu_length: int | None = Field(default=None)
    ssu_silva_blast_evalue: float | None = Field(default=None)
    ssu_silva_blast_perc_identity: float | None = Field(default=None)
    lsu_5s_query_id: str | None = Field(default=None)
    lsu_5s_length: int | None = Field(default=None)
    lsu_5s_contig_len: int | None = Field(default=None)


class DbMetadataRrnaSequences(SQLModel, table=True):
    __tablename__ = 'metadata_rrna_sequences'

    id: int = Field(primary_key=True, foreign_key='genomes.id')
    lsu_23s_sequence: str | None = Field(default=None)
    ssu_sequence: str | None = Field(default=None)
    lsu_5s_sequence: str | None = Field(default=None)


class DbMetadataSeqcode(SQLModel, table=True):
    __tablename__ = 'metadata_seqcode'

    id: int = Field(primary_key=True, foreign_key='genomes.id')
    seqcode_id: int | None = Field(default=None)
    seqcode_name: str | None = Field(default=None)
    seqcode_rank: str | None = Field(default=None)
    seqcode_species_status: str | None = Field(default=None)
    seqcode_genus_status: str | None = Field(default=None)
    seqcode_family_status: str | None = Field(default=None)
    seqcode_order_status: str | None = Field(default=None)
    seqcode_class_status: str | None = Field(default=None)
    seqcode_phylum_status: str | None = Field(default=None)
    seqcode_type_species_of_genus: bool | None = Field(default=None)
    seqcode_type_genus_of_family: bool | None = Field(default=None)
    seqcode_type_genus_of_order: bool | None = Field(default=None)
    seqcode_type_genus_of_class: bool | None = Field(default=None)
    seqcode_type_genus_of_phylum: bool | None = Field(default=None)
    seqcode_classification: str | None = Field(default=None)
    seqcode_proposed_by: str | None = Field(default=None)
    seqcode_created_at: str | None = Field(default=None)
    seqcode_updated_at: str | None = Field(default=None)
    seqcode_url: str | None = Field(default=None)
    seqcode_priority_date: str | None = Field(default=None)


class DbMetadataTaxonomy(SQLModel, table=True):
    __tablename__ = 'metadata_taxonomy'

    id: int = Field(primary_key=True, foreign_key='genomes.id')
    ncbi_taxonomy: str | None = Field(default=None)
    gtdb_class: str | None = Field(default=None)
    gtdb_species: str | None = Field(default=None)
    gtdb_phylum: str | None = Field(default=None)
    gtdb_family: str | None = Field(default=None)
    gtdb_domain: str | None = Field(default=None)
    gtdb_order: str | None = Field(default=None)
    gtdb_genus: str | None = Field(default=None)
    gtdb_genome_representative: str | None = Field(default=None)
    gtdb_representative: bool | None = Field(default=None)
    ncbi_taxonomy_unfiltered: str | None = Field(default=None)
    ncbi_type_material_designation: str | None = Field(default=None)


class DbMetadataTypeMaterial(SQLModel, table=True):
    __tablename__ = 'metadata_type_material'

    id: int = Field(primary_key=True, foreign_key='genomes.id')
    gtdb_type_designation_ncbi_taxa: str | None = Field(default=None)
    gtdb_type_designation_ncbi_taxa_sources: str | None = Field(default=None)
    lpsn_type_designation: str | None = Field(default=None)
    dsmz_type_designation: str | None = Field(default=None)
    lpsn_priority_year: int | None = Field(default=None)
    gtdb_type_species_of_genus: bool | None = Field(default=None)


class DbSurveyGenomes(SQLModel, table=True):
    __tablename__ = 'survey_genomes'

    canonical_gid: str = Field(sa_column=Column(CHAR(20), primary_key=True))


class DbUserRoles(SQLModel, table=True):
    __tablename__ = 'user_roles'

    id: int = Field(primary_key=True)
    name: str = Field()


class DbUsers(SQLModel, table=True):
    __tablename__ = 'users'

    id: int | None = Field(primary_key=True, default=None)
    username: str = Field()
    role_id: int = Field(foreign_key="user_roles.id")
    has_root_login: bool = Field(default=False)
    firstname: str = Field()
    lastname: str = Field()


"""
Materialized views below.
"""


class DbGtdbSearchMtView(SQLModel, table=True):
    __tablename__ = 'gtdb_search_mtview'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id_at_source: str | None = Field()
    ncbi_organism_name: str | None = Field()
    ncbi_taxonomy: str | None = Field()
    gtdb_taxonomy: str | None = Field()
    ncbi_genbank_assembly_accession: str | None = Field()
    ncbi_type_material_designation: str | None = Field()
    gtdb_representative: bool | None = Field()
    formatted_source_id: str | None = Field()


class DbGtdbSpeciesClusterCount(SQLModel, table=True):
    __tablename__ = 'gtdb_species_cluster_count'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    gtdb_domain: str | None = Field()
    gtdb_phylum: str | None = Field()
    gtdb_class: str | None = Field()
    gtdb_order: str | None = Field()
    gtdb_family: str | None = Field()
    gtdb_genus: str | None = Field()
    gtdb_species: str | None = Field()
    cnt: int | None = Field()


class DbGtdbTaxonomyMtView(SQLModel, table=True):
    __tablename__ = 'gtdb_taxonomy_mtview'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    gtdb_taxonomy: str | None = Field()


class DbGtdbTreeCount(SQLModel, table=True):
    __tablename__ = 'gtdb_tree_count'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    parent: str | None = Field()
    child: str | None = Field()
    total: int | None = Field()


class DbMetadataMtView(SQLModel, table=True):
    __tablename__ = 'metadata_mtview'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    accession: str | None = Field()
    formatted_accession: str | None = Field()
    organism_name: str | None = Field()
    description: str | None = Field()
    username: str | None = Field()
    scaffold_count: int | None = Field()
    gc_count: int | None = Field()
    longest_scaffold: int | None = Field()
    gc_percentage: float | None = Field()
    total_gap_length: int | None = Field()
    genome_size: int | None = Field()
    n50_contigs: int | None = Field()
    n50_scaffolds: int | None = Field()
    l50_scaffolds: int | None = Field()
    contig_count: int | None = Field()
    ambiguous_bases: int | None = Field()
    longest_contig: int | None = Field()
    l50_contigs: int | None = Field()
    mean_scaffold_length: int | None = Field()
    mean_contig_length: int | None = Field()
    trna_aa_count: int | None = Field()
    trna_selenocysteine_count: int | None = Field()
    trna_count: int | None = Field()
    checkm_completeness: float | None = Field()
    checkm_contamination: float | None = Field()
    protein_count: int | None = Field()
    coding_bases: int | None = Field()
    coding_density: float | None = Field()
    ssu_count: int | None = Field()
    checkm_marker_count: int | None = Field()
    checkm_marker_lineage: str | None = Field()
    checkm_genome_count: int | None = Field()
    checkm_marker_set_count: int | None = Field()
    checkm_strain_heterogeneity: float | None = Field()
    lsu_23s_count: int | None = Field()
    lsu_5s_count: int | None = Field()
    checkm_strain_heterogeneity_100: float | None = Field()
    checkm2_completeness: float | None = Field()
    checkm2_contamination: float | None = Field()
    checkm2_model: str | None = Field()
    ncbi_taxonomy: str | None = Field()
    gtdb_class: str | None = Field()
    gtdb_species: str | None = Field()
    gtdb_phylum: str | None = Field()
    gtdb_family: str | None = Field()
    gtdb_domain: str | None = Field()
    gtdb_order: str | None = Field()
    gtdb_genus: str | None = Field()
    gtdb_genome_representative: str | None = Field()
    gtdb_representative: bool | None = Field()
    ncbi_taxonomy_unfiltered: str | None = Field()
    ncbi_type_material_designation: str | None = Field()
    ncbi_biosample: str | None = Field()
    ncbi_total_gap_length: int | None = Field()
    ncbi_molecule_count: int | None = Field()
    ncbi_date: str | None = Field()
    ncbi_submitter: str | None = Field()
    ncbi_ncrna_count: int | None = Field()
    ncbi_scaffold_n50: int | None = Field()
    ncbi_assembly_name: str | None = Field()
    ncbi_scaffold_n75: int | None = Field()
    ncbi_protein_count: int | None = Field()
    ncbi_assembly_type: str | None = Field()
    ncbi_rrna_count: int | None = Field()
    ncbi_genbank_assembly_accession: str | None = Field()
    ncbi_total_length: int | None = Field()
    ncbi_unspanned_gaps: int | None = Field()
    ncbi_taxid: int | None = Field()
    ncbi_trna_count: int | None = Field()
    ncbi_genome_representation: str | None = Field()
    ncbi_top_level_count: int | None = Field()
    ncbi_spanned_gaps: int | None = Field()
    ncbi_translation_table: int | None = Field()
    ncbi_scaffold_n90: int | None = Field()
    ncbi_contig_count: int | None = Field()
    ncbi_organism_name: str | None = Field()
    ncbi_region_count: int | None = Field()
    ncbi_contig_n50: int | None = Field()
    ncbi_ungapped_length: int | None = Field()
    ncbi_scaffold_l50: int | None = Field()
    ncbi_ssu_count: int | None = Field()
    ncbi_scaffold_count: int | None = Field()
    ncbi_assembly_level: str | None = Field()
    ncbi_refseq_assembly_and_genbank_assemblies_identical: str | None = Field()
    ncbi_release_type: str | None = Field()
    ncbi_refseq_category: str | None = Field()
    ncbi_species_taxid: str | None = Field()
    ncbi_isolate: str | None = Field()
    ncbi_version_status: str | None = Field()
    ncbi_wgs_master: str | None = Field()
    ncbi_asm_name: str | None = Field()
    ncbi_bioproject: str | None = Field()
    ncbi_paired_asm_comp: str | None = Field()
    ncbi_seq_rel_date: str | None = Field()
    ncbi_gbrs_paired_asm: str | None = Field()
    ncbi_isolation_source: str | None = Field()
    ncbi_country: str | None = Field()
    ncbi_lat_lon: str | None = Field()
    ncbi_strain_identifiers: str | None = Field()
    ncbi_genome_category: str | None = Field()
    ncbi_wgs_formatted: str | None = Field()
    ncbi_cds_count: int | None = Field()
    ncbi_not_used_as_type: bool | None = Field()
    ncbi_excluded_from_refseq: str | None = Field()
    ssu_gg_taxonomy: str | None = Field()
    ssu_gg_blast_bitscore: float | None = Field()
    ssu_gg_blast_subject_id: str | None = Field()
    ssu_gg_blast_perc_identity: float | None = Field()
    ssu_gg_blast_evalue: float | None = Field()
    ssu_gg_blast_align_len: int | None = Field()
    ssu_gg_query_id: str | None = Field()
    ssu_gg_length: int | None = Field()
    lsu_23s_contig_len: int | None = Field()
    ssu_contig_len: int | None = Field()
    lsu_silva_23s_blast_bitscore: float | None = Field
    lsu_silva_23s_taxonomy: str | None = Field()
    lsu_silva_23s_blast_subject_id: str | None = Field
    lsu_23s_query_id: str | None = Field()
    lsu_silva_23s_blast_align_len: int | None = Field
    lsu_23s_length: int | None = Field()
    lsu_silva_23s_blast_evalue: float | None = Field
    lsu_silva_23s_blast_perc_identity: float | None = Field
    ssu_silva_blast_bitscore: float | None = Field()
    ssu_silva_taxonomy: str | None = Field()
    ssu_silva_blast_subject_id: str | None = Field()
    ssu_query_id: str | None = Field()
    ssu_silva_blast_align_len: int | None = Field()
    ssu_length: int | None = Field()
    ssu_silva_blast_evalue: float | None = Field()
    ssu_silva_blast_perc_identity: float | None = Field()
    lsu_5s_query_id: str | None = Field()
    lsu_5s_length: int | None = Field()
    lsu_5s_contig_len: int | None = Field()
    seqcode_id: int | None = Field()
    seqcode_name: str | None = Field()
    seqcode_rank: str | None = Field()
    seqcode_species_status: str | None = Field()
    seqcode_genus_status: str | None = Field()
    seqcode_family_status: str | None = Field()
    seqcode_order_status: str | None = Field()
    seqcode_class_status: str | None = Field()
    seqcode_phylum_status: str | None = Field()
    seqcode_type_species_of_genus: bool | None = Field()
    seqcode_type_genus_of_family: bool | None = Field()
    seqcode_type_genus_of_order: bool | None = Field()
    seqcode_type_genus_of_class: bool | None = Field()
    seqcode_type_genus_of_phylum: bool | None = Field()
    seqcode_classification: str | None = Field()
    seqcode_proposed_by: str | None = Field()
    seqcode_created_at: str | None = Field()
    seqcode_updated_at: str | None = Field()
    seqcode_url: str | None = Field()
    seqcode_priority_date: str | None = Field()
    gtdb_taxonomy: str | None = Field()
    mimag_high_quality: bool | None = Field()
    mimag_medium_quality: bool | None = Field()
    mimag_low_quality: bool | None = Field()
    gtdb_genus_type_species: bool | None = Field()
    gtdb_species_type_strain: bool | None = Field()
    gtdb_cluster_size: bool | None = Field()
    gtdb_clustered_genomes: str | None = Field()
    gtdb_type_designation_ncbi_taxa: str | None = Field()
    gtdb_type_designation_ncbi_taxa_sources: str | None = Field()
    lpsn_type_designation: str | None = Field()
    dsmz_type_designation: str | None = Field()
    lpsn_priority_year: int | None = Field()
    gtdb_type_species_of_genus: bool | None = Field()


class DbUbaMtView(SQLModel, table=True):
    __tablename__ = 'uba_mtview'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    uba_number: str | None = Field()


"""
Views below.
"""


class DbAlignedMarkersView(SQLModel, table=True):
    __tablename__ = 'aligned_markers_view'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    genome_id: int | None = Field()
    count: int | None = Field()
    set_id: int | None = Field()
    evalue: int | None = Field()


class DbGtdbTaxonomyView(SQLModel, table=True):
    __tablename__ = 'gtdb_taxonomy_view'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    gtdb_taxonomy: str | None = Field()


class DbGtdbTypeSpeciesView(SQLModel, table=True):
    __tablename__ = 'gtdb_type_species_view'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    gtdb_type_designation_gtdb_taxa: str | None = Field()
    gtdb_genus_type_species: bool | None = Field()


class DbGtdbTypeView(SQLModel, table=True):
    __tablename__ = 'gtdb_type_view'

    # This is required to satisfy the dependency that all tables must have primary keys.

    id: int | None = Field(primary_key=True)
    gtdb_genus_type_species: bool | None = Field()
    gtdb_species_type_strain: bool | None = Field()


# metadata_view is not done in favour of the materialized view.

class DbMiMagQualityView(SQLModel, table=True):
    __tablename__ = 'mimag_quality_view'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    mimag_high_quality: bool | None = Field()
    mimag_medium_quality: bool | None = Field()
    mimag_low_quality: bool | None = Field()


class DbRepresentativeStatsView(SQLModel, table=True):
    __tablename__ = 'representative_stats_view'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    accession: str | None = Field()
    gtdb_cluster_size: int | None = Field()
    gtdb_clustered_genomes: str | None = Field()


# sra_dereplicated has not been done as it's not used anywhere.

class DbUbaView(SQLModel, table=True):
    __tablename__ = 'uba_view'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    id: int | None = Field()
    uba_number: str | None = Field()


class DbViewListMetaColumns(SQLModel, table=True):
    __tablename__ = 'view_list_meta_columns'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    table: str | None = Field()
    field: str | None = Field()
    data_type: str | None = Field()
    description: str | None = Field()


class DbWebGtdbStats(SQLModel, table=True):
    __tablename__ = 'web_gtdb_stats'

    # This is required to satisfy the dependency that all tables must have primary keys.
    column_that_doesnt_exist: int = Field(primary_key=True)

    database: str | None = Field()
    gtdb_domain: str | None = Field()
    total_count: int | None = Field()
    qc_passed: int | None = Field()
    qc_failed: int | None = Field()
    representatives: int | None = Field()
