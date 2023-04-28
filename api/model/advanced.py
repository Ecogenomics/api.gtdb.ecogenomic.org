from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from api.db.models import MetadataView


class AdvancedSearchOption(Enum):

    def __init__(self, uid: int, display: str, keyword: str):
        self.id = uid
        self.display: str = display
        self.keyword: str = keyword

    def json(self):
        return {
            'id': self.id,
            'display': self.display
        }

    """
    Note: Each enum must have a unique ID as this is used to generate 
    the URL. New enums should not re-use old IDs, and IDs should not be changed.
    """
    NOT_TYPE_MAT = 0, 'not type material', 'not type material'
    TYPE_STRAIN_OF_SPECIES = 1, 'type strain of species', 'type strain of species'
    TYPE_STRAIN_OF_SUBSP = 2, 'type strain of subspecies', 'type strain of subspecies'
    TYPE_STRAIN_OF_HETERO = 3, 'type strain of heterotypic synonym', 'type strain of heterotypic synonym'
    CONTIG = 4, 'contig', 'Contig'
    SCAFFOLD = 5, 'scaffold', 'Scaffold'
    COMPLETE_GENOME = 6, 'complete genome', 'Complete Genome'
    DERIVED_METAGENOME = 7, 'derived from metagenome', 'derived from metagenome'
    DERIVED_ENV_SAMPLE = 8, 'derived from environmental sample', 'derived from environmental sample'
    DERIVED_SINGLE_CELL = 9, 'derived from single cell', 'derived from single cell'
    FULL = 10, 'full', 'full'
    PARTIAL = 11, 'partial', 'partial'
    REP_GENOME = 12, 'representative genome', 'representative genome'
    REF_GENOME = 13, 'reference genome', 'reference genome'
    ASSEMBLY_FROM_TYPE = 14, 'assembly from type material', 'assembly from type material'
    ASSEMBLY_FROM_SYNONYM = 15, 'assembly from synonym type material', 'assembly from synonym type material'
    ASSEMBLY_FROM_PATHO = 16, 'assembly from pathotype material', 'assembly from pathotype material'
    ASSEMBLY_DESIGNATED_REF = 17, 'assembly designated as reftype', 'assembly designated as reftype'
    ASSEMBLY_DESIGNATED_NEO = 18, 'assembly designated as neotype', 'assembly designated as neotype'
    CHROMOSOME = 19, 'chromosome', 'Chromosome'
    NULL = 20, 'N/A', None


class AdvancedDataType(Enum):
    STRING = 'string'
    DATE = 'date'
    BOOLEAN = 'boolean'
    NUMERIC = 'numeric'
    ENUM = 'enum'

    def json(self):
        return {'name': self.name, 'value': self.value}


class AdvancedSearchOperator(Enum):

    def __init__(self, uid: int, display: str, dt: AdvancedDataType, operator: str):
        self.id = uid
        self.display: str = display
        self.dt: AdvancedDataType = dt
        self.operator: str = operator

    def json(self):
        return {
            'id': self.id,
            'display': self.display,
            'dataType': self.dt.value,
        }

    """
    Note: Each enum must have a unique ID as this is used to generate 
    the URL. New enums should not re-use old IDs, and IDs should not be changed.
    """
    STR_IS = 0, 'IS', AdvancedDataType.STRING, '='
    STR_IS_NOT = 1, 'IS NOT', AdvancedDataType.STRING, '!='
    STR_CONTAINS = 2, 'CONTAINS', AdvancedDataType.STRING, 'ILIKE'
    DATE_BEFORE = 3, 'BEFORE', AdvancedDataType.DATE, '<'
    DATE_ON = 4, 'ON', AdvancedDataType.DATE, '='
    DATE_AFTER = 5, 'AFTER', AdvancedDataType.DATE, '>'
    BOOL_TRUE = 6, 'TRUE', AdvancedDataType.BOOLEAN, 'TRUE'
    BOOL_FALSE = 7, 'FALSE', AdvancedDataType.BOOLEAN, 'FALSE'
    NUM_EQ = 8, '=', AdvancedDataType.NUMERIC, '='
    NUM_LE = 9, '<', AdvancedDataType.NUMERIC, '<'
    NUM_LEQ = 10, '<=', AdvancedDataType.NUMERIC, '<='
    NUM_GT = 11, '>', AdvancedDataType.NUMERIC, '>'
    NUM_GTE = 12, '>=', AdvancedDataType.NUMERIC, '>='
    NUM_NE = 13, '!=', AdvancedDataType.NUMERIC, '!='
    ENUM_IS = 14, 'IS', AdvancedDataType.ENUM, '='
    ENUM_IS_NOT = 15, 'IS NOT', AdvancedDataType.ENUM, '!='


class AdvancedSearchColumn(Enum):

    def __init__(self, uid: int, display: str, dt: AdvancedDataType, column, options: List[AdvancedSearchOption],
                 group: str):
        self.id = uid
        self.display: str = display
        self.dt: AdvancedDataType = dt
        self.column = column  # self.column.key
        self.options = options
        self.group = group

    def json(self):
        return {'id': self.id, 'display': self.display, 'dataType': self.dt.value,
                'options': [x.json() for x in self.options] if self.options else None,
                'group': self.group}

    """
    Note: Each enum must have a unique ID as this is used to generate 
    the URL. New enums should not re-use old IDs, and IDs should not be changed.
    """
    ACCESSION = 0, 'Accession', AdvancedDataType.STRING, MetadataView.organism_name, [], 'General'
    GTDB_TAXONOMY = 1, 'GTDB Taxonomy', AdvancedDataType.STRING, MetadataView.gtdb_taxonomy, [], 'Taxonomic Information'
    NCBI_TAXONOMY = 2, 'NCBI Taxonomy', AdvancedDataType.STRING, MetadataView.ncbi_taxonomy, [], 'Taxonomic Information'
    NCBI_STRAIN_ID = 3, 'NCBI Strain Identifiers', AdvancedDataType.STRING, MetadataView.ncbi_strain_identifiers, [], 'Taxonomic Information'
    GTDB_TYPE_MAT = 4, 'GTDB Type Material', AdvancedDataType.ENUM, MetadataView.gtdb_type_designation_ncbi_taxa, \
                    [AdvancedSearchOption.NOT_TYPE_MAT,
                     AdvancedSearchOption.TYPE_STRAIN_OF_SPECIES,
                     AdvancedSearchOption.TYPE_STRAIN_OF_SUBSP,
                     AdvancedSearchOption.TYPE_STRAIN_OF_HETERO], 'Taxonomic Information'
    GTDB_REP_OF_SPECIES = 5, 'GTDB Representative of Species', AdvancedDataType.BOOLEAN, MetadataView.gtdb_representative, [], 'Taxonomic Information'
    CHECKM_COMPLETENESS = 6, 'CheckM Completeness', AdvancedDataType.NUMERIC, MetadataView.checkm_completeness, [], 'Genome Characteristics'
    CHECKM_CONTAM = 7, 'CheckM Contamination', AdvancedDataType.NUMERIC, MetadataView.checkm_contamination, [], 'Genome Characteristics'
    CHECKM_STRAIN_HETERO = 8, 'CheckM Strain Heterogeneity', AdvancedDataType.NUMERIC, MetadataView.checkm_strain_heterogeneity, [], 'Genome Characteristics'
    CNT_5S = 9, '5S Count', AdvancedDataType.NUMERIC, MetadataView.lsu_5s_count, [], 'Genome Characteristics'
    CNT_16S = 10, '16S Count', AdvancedDataType.NUMERIC, MetadataView.ssu_count, [], 'Genome Characteristics'
    CNT_23S = 11, '23S Count', AdvancedDataType.NUMERIC, MetadataView.lsu_23s_count, [], 'Genome Characteristics'
    TRNA_COUNT = 12, 'tRNA Count', AdvancedDataType.NUMERIC, MetadataView.trna_aa_count, [], 'Genome Characteristics'
    CONTIG_COUNT = 13, 'Contig Count', AdvancedDataType.NUMERIC, MetadataView.contig_count, [], 'Genome Characteristics'
    N50_CONTIGS = 14, 'N50 Contigs', AdvancedDataType.NUMERIC, MetadataView.n50_contigs, [], 'Genome Characteristics'
    LONGEST_CONTIG = 15, 'Longest Contig', AdvancedDataType.NUMERIC, MetadataView.longest_contig, [], 'Genome Characteristics'
    SCAFFOLD_COUNT = 16, 'Scaffold Count', AdvancedDataType.NUMERIC, MetadataView.longest_scaffold, [], 'Genome Characteristics'
    N50_SCAFFOLDS = 17, 'N50 Scaffolds', AdvancedDataType.NUMERIC, MetadataView.n50_scaffolds, [], 'Genome Characteristics'
    LONGEST_SCAFFOLD = 18, 'Longest Scaffold', AdvancedDataType.NUMERIC, MetadataView.longest_scaffold, [], 'Genome Characteristics'
    GENOME_SIZE = 19, 'Genome Size', AdvancedDataType.NUMERIC, MetadataView.genome_size, [], 'Genome Characteristics'
    PROTEIN_COUNT = 20, 'Protein Count', AdvancedDataType.NUMERIC, MetadataView.protein_count, [], 'Genome Characteristics'
    CODING_DENSITY = 21, 'Coding Density', AdvancedDataType.NUMERIC, MetadataView.coding_density, [], 'Genome Characteristics'
    GC_PCT = 22, 'GC Percentage', AdvancedDataType.NUMERIC, MetadataView.gc_percentage, [], 'Genome Characteristics'
    AMBIGUOUS_BASES = 23, 'Ambiguous Bases', AdvancedDataType.NUMERIC, MetadataView.ambiguous_bases, [], 'Genome Characteristics'
    ASSEMBLY_LEVEL = 24, 'Assembly Level', AdvancedDataType.ENUM, MetadataView.ncbi_assembly_level, \
                     [AdvancedSearchOption.CONTIG,
                      AdvancedSearchOption.SCAFFOLD,
                      AdvancedSearchOption.COMPLETE_GENOME,
                      AdvancedSearchOption.CHROMOSOME], 'NCBI Metadata'
    ASSEMBLY_NAME = 25, 'Assembly Name', AdvancedDataType.STRING, MetadataView.ncbi_assembly_name, [], 'NCBI Metadata'
    ASSEMBLY_TYPE = 26, 'Assembly Type', AdvancedDataType.STRING, MetadataView.ncbi_assembly_type, [], 'NCBI Metadata'
    BIOPROJECT = 27, 'Bioproject', AdvancedDataType.STRING, MetadataView.ncbi_bioproject, [], 'NCBI Metadata'
    BIOSAMPLE = 28, 'Biosample', AdvancedDataType.STRING, MetadataView.ncbi_biosample, [], 'NCBI Metadata'
    COUNTRY = 29, 'Country', AdvancedDataType.STRING, MetadataView.ncbi_country, [], 'NCBI Metadata'
    DATE = 30, 'Date', AdvancedDataType.DATE, MetadataView.ncbi_date, [], 'NCBI Metadata'
    GENBANK_ASSEMBLY_ACCESSION = 31, 'Genbank Assembly Accession', AdvancedDataType.STRING, MetadataView.ncbi_genbank_assembly_accession, [], 'NCBI Metadata'
    GENOME_CATEGORY = 32, 'Genome Category', AdvancedDataType.ENUM, MetadataView.ncbi_genome_category, [
        AdvancedSearchOption.DERIVED_METAGENOME,
        AdvancedSearchOption.DERIVED_ENV_SAMPLE,
        AdvancedSearchOption.DERIVED_SINGLE_CELL,
        AdvancedSearchOption.NULL], 'NCBI Metadata'
    GENOME_REPRESENTATION = 33, 'Genome Representation', AdvancedDataType.ENUM, MetadataView.ncbi_genome_representation, \
                            [AdvancedSearchOption.FULL,
                             AdvancedSearchOption.PARTIAL], 'NCBI Metadata'
    ISOLATE = 34, 'Isolate', AdvancedDataType.STRING, MetadataView.ncbi_isolate, [], 'NCBI Metadata'
    ISOLATION_SOURCE = 35, 'Isolation Source', AdvancedDataType.STRING, MetadataView.ncbi_isolation_source, [], 'NCBI Metadata'
    MOLECULE_COUNT = 36, 'Molecule Count', AdvancedDataType.NUMERIC, MetadataView.ncbi_molecule_count, [], 'NCBI Metadata'
    ORGANISM_NAME = 37, 'Organism Name', AdvancedDataType.STRING, MetadataView.ncbi_organism_name, [], 'NCBI Metadata'
    CDS_COUNT = 38, 'CDS Count', AdvancedDataType.NUMERIC, MetadataView.ncbi_cds_count, [], 'NCBI Metadata'
    REFSEQ_CATEGORY = 39, 'Refseq Category', AdvancedDataType.ENUM, MetadataView.ncbi_refseq_category, \
                      [AdvancedSearchOption.REP_GENOME,
                       AdvancedSearchOption.REF_GENOME], 'NCBI Metadata'
    SPANNED_GAPS = 40, 'Spanned Gaps', AdvancedDataType.NUMERIC, MetadataView.ncbi_spanned_gaps, [], 'NCBI Metadata'
    NCBI_SPECIES_TAXID = 41, 'NCBI Species Taxonomy ID', AdvancedDataType.NUMERIC, MetadataView.ncbi_species_taxid, [], 'NCBI Metadata'
    SSU_COUNT = 42, 'SSU Count', AdvancedDataType.NUMERIC, MetadataView.ncbi_ssu_count, [], 'NCBI Metadata'
    SUBMITTER = 43, 'Submitter', AdvancedDataType.STRING, MetadataView.ncbi_submitter, [], 'NCBI Metadata'
    NCBI_TAXID = 44, 'NCBI Taxonomy ID', AdvancedDataType.NUMERIC, MetadataView.ncbi_taxid, [], 'NCBI Metadata'
    TOTAL_GAP_LEN = 45, 'Total Gap Length', AdvancedDataType.NUMERIC, MetadataView.ncbi_total_gap_length, [], 'NCBI Metadata'
    TLN_TABLE = 46, 'Translation Table', AdvancedDataType.NUMERIC, MetadataView.ncbi_translation_table, [], 'NCBI Metadata'
    TRNA_TOTAL = 47, 'tRNA Count (total)', AdvancedDataType.NUMERIC, MetadataView.ncbi_trna_count, [], 'NCBI Metadata'
    TYPE_MATERIAL = 48, 'Type Material', AdvancedDataType.ENUM, MetadataView.ncbi_type_material_designation, \
                    [AdvancedSearchOption.ASSEMBLY_FROM_TYPE,
                     AdvancedSearchOption.ASSEMBLY_FROM_SYNONYM,
                     AdvancedSearchOption.ASSEMBLY_FROM_PATHO,
                     AdvancedSearchOption.ASSEMBLY_DESIGNATED_REF,
                     AdvancedSearchOption.ASSEMBLY_DESIGNATED_NEO,
                     AdvancedSearchOption.NULL], 'NCBI Metadata'
    UNSPANNED_GAPS = 49, 'Unspanned Gaps', AdvancedDataType.NUMERIC, MetadataView.ncbi_unspanned_gaps, [], 'NCBI Metadata'
    VERSION_STATUS = 50, 'Version Status', AdvancedDataType.STRING, MetadataView.ncbi_version_status, [], 'NCBI Metadata'
    WGS_MASTER = 51, 'WGS Master', AdvancedDataType.STRING, MetadataView.ncbi_wgs_master, [], 'NCBI Metadata'


class AdvancedSearchOptionsResponse(BaseModel):
    """An option that can be used in the advanced search."""
    id: int = Field(...)
    display: str = Field(...)


class AdvancedSearchDataTypeResponse(BaseModel):
    """A data type that can be used in the advanced search."""
    name: str = Field(...)
    value: str = Field(...)


class AdvancedSearchOperatorResponse(BaseModel):
    """An operator that can be used in the advanced search."""
    id: int = Field(...)
    display: str = Field(...)
    dataType: str = Field(...)


class AdvancedSearchColumnResponse(BaseModel):
    """A column that can be used in the advanced search."""
    id: int = Field(...)
    display: str = Field(...)
    dataType: str = Field(...)
    options: Optional[List[AdvancedSearchOptionsResponse]] = Field(None)
    group: str = Field(...)


class AdvancedSearchHeader(BaseModel):
    text: str = Field(...)
    value: str = Field(...)


class AdvancedSearchResult(BaseModel):
    headers: List[AdvancedSearchHeader] = Field(...)
    rows: List[Dict[str, Any]] = Field(...)
