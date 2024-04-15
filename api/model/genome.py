from typing import Optional, List

from pydantic import BaseModel, Field


class GenomeMetadata(BaseModel):
    accession: str = Field(..., title="GTDB accession")
    isNcbiSurveillance: Optional[bool] = Field(False, title="Is a NCBI surveillance genome?")


class GenomeTaxonHistory(BaseModel):
    """A genome taxonomy for a specific release."""
    release: str = Field(..., title="Release")
    d: str = Field(..., description='domain', example='Bacteria')
    p: str = Field(..., description='phylum', example='Proteobacteria')
    c: str = Field(..., description='class', example='Gammaproteobacteria')
    o: str = Field(..., description='order', example='Enterobacterales')
    f: str = Field(..., description='family', example='Enterobacteriaceae')
    g: str = Field(..., description='genus', example='Escherichia')
    s: str = Field(..., description='species', example='Escherichia coli')



class GenomeBase(BaseModel):
    accession: Optional[str] = Field(None)
    name: Optional[str] = Field(None)


class GenomeMetadataNucleotide(BaseModel):
    trna_aa_count: Optional[int] = Field(None)
    contig_count: Optional[int] = Field(None)
    n50_contigs: Optional[int] = Field(None)
    longest_contig: Optional[int] = Field(None)
    scaffold_count: Optional[int] = Field(None)
    n50_scaffolds: Optional[int] = Field(None)
    longest_scaffold: Optional[int] = Field(None)
    genome_size: Optional[int] = Field(None)
    gc_percentage: Optional[float] = Field(None)
    ambiguous_bases: Optional[int] = Field(None)

class GenomeMetadataGene(BaseModel):
    checkm_completeness: Optional[str] = Field(None)
    checkm_contamination: Optional[str] = Field(None)
    checkm_strain_heterogeneity: Optional[str] = Field(None)
    checkm2_completeness: Optional[str] = Field(None)
    checkm2_contamination: Optional[str] = Field(None)
    checkm2_model: Optional[str] = Field(None)
    lsu_5s_count: Optional[str] = Field(None)
    ssu_count: Optional[str] = Field(None)
    lsu_23s_count: Optional[str] = Field(None)
    protein_count: Optional[str] = Field(None)
    coding_density: Optional[str] = Field(None)

class GenomeMetadataNcbi(BaseModel):
    ncbi_genbank_assembly_accession: Optional[str] = Field(None)
    ncbi_strain_identifiers: Optional[str] = Field(None)
    ncbi_assembly_level: Optional[str] = Field(None)
    ncbi_assembly_name: Optional[str] = Field(None)
    ncbi_assembly_type: Optional[str] = Field(None)
    ncbi_bioproject: Optional[str] = Field(None)
    ncbi_biosample: Optional[str] = Field(None)
    ncbi_country: Optional[str] = Field(None)
    ncbi_date: Optional[str] = Field(None)
    ncbi_genome_category: Optional[str] = Field(None)
    ncbi_genome_representation: Optional[str] = Field(None)
    ncbi_isolate: Optional[str] = Field(None)
    ncbi_isolation_source: Optional[str] = Field(None)
    ncbi_lat_lon: Optional[str] = Field(None)
    ncbi_molecule_count: Optional[str] = Field(None)
    ncbi_cds_count: Optional[str] = Field(None)
    ncbi_refseq_category: Optional[str] = Field(None)
    ncbi_seq_rel_date: Optional[str] = Field(None)
    ncbi_spanned_gaps: Optional[str] = Field(None)
    ncbi_species_taxid: Optional[str] = Field(None)
    ncbi_ssu_count: Optional[str] = Field(None)
    ncbi_submitter: Optional[str] = Field(None)
    ncbi_taxid: Optional[str] = Field(None)
    ncbi_total_gap_length: Optional[str] = Field(None)
    ncbi_translation_table: Optional[str] = Field(None)
    ncbi_trna_count: Optional[str] = Field(None)
    ncbi_unspanned_gaps: Optional[str] = Field(None)
    ncbi_version_status: Optional[str] = Field(None)
    ncbi_wgs_master: Optional[str] = Field(None)


class GenomeMetadataTaxonomy(BaseModel):
    ncbi_taxonomy: Optional[str] = Field(None)
    ncbi_taxonomy_unfiltered: Optional[str] = Field(None)
    gtdb_representative: Optional[bool] = Field(None)
    gtdb_genome_representative: Optional[str] = Field(None)
    ncbi_type_material_designation: Optional[str] = Field(None)
    gtdbDomain: Optional[str] = Field(None)
    gtdbPhylum: Optional[str] = Field(None)
    gtdbClass: Optional[str] = Field(None)
    gtdbOrder: Optional[str] = Field(None)
    gtdbFamily: Optional[str] = Field(None)
    gtdbGenus: Optional[str] = Field(None)
    gtdbSpecies: Optional[str] = Field(None)



class GenomeNcbiTaxon(BaseModel):
    taxon: str = Field(...)
    taxonId: str = Field(None)


class GenomeMetadataTypeMaterial(BaseModel):
    gtdbTypeDesignation: Optional[str] = Field(None)
    gtdbTypeDesignationSources: Optional[str] = Field(None)
    lpsnTypeDesignation: Optional[str] = Field(None)
    dsmzTypeDesignation: Optional[str] = Field(None)
    lpsnPriorityYear: Optional[int] = Field(None)
    gtdbTypeSpeciesOfGenus: Optional[bool] = Field(None)


class GenomeCard(BaseModel):
    genome: Optional[GenomeBase] = Field(None)
    metadata_nucleotide: Optional[GenomeMetadataNucleotide] = Field(None)
    metadata_gene: Optional[GenomeMetadataGene] = Field(None)
    metadata_ncbi: Optional[GenomeMetadataNcbi] = Field(None)
    metadata_type_material: Optional[GenomeMetadataTypeMaterial] = Field(None)
    metadataTaxonomy: Optional[GenomeMetadataTaxonomy] = Field(None)
    gtdbTypeDesignation: Optional[str] = Field(None)
    subunit_summary: Optional[str] = Field(None)
    speciesRepName: Optional[str] = Field(None)
    speciesClusterCount: Optional[int] = Field(None)
    lpsnUrl: Optional[str] = Field(None)
    link_ncbi_taxonomy: Optional[str] = Field(None)
    link_ncbi_taxonomy_unfiltered: Optional[str] = Field(None)
    ncbiTaxonomyFiltered: Optional[List[GenomeNcbiTaxon]] = Field(None)
    ncbiTaxonomyUnfiltered: Optional[List[GenomeNcbiTaxon]] = Field(None)


