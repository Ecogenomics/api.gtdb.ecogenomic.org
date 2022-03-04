from typing import List, Optional

from pydantic import BaseModel, Field


class SpeciesClusterGenome(BaseModel):
    accession: str = Field(..., description='genome accession', example='GCA_000405245.1')
    ncbi_org_name: str = Field(..., description='NCBI organism name',
                               example='Candidatus Aenigmarchaeum subterraneum SCGC AAA011-O16')
    ncbi_tax: str = Field(..., description='NCBI taxonomy string',
                          example='d__Archaea; p__Candidatus Aenigmarchaeota; c__; o__; f__; g__Candidatus Aenigmarchaeum; s__Candidatus Aenigmarchaeum subterraneum')
    gtdb_species_rep: bool = Field(..., description='is this a GTDB species representative', example=True)
    ncbi_type_material: Optional[str] = Field(None, description='is this NCBI type materia',
                                              example='assembly from type material')


class SpeciesCluster(BaseModel):
    """Information about a species."""
    name: str = Field(..., description='species to display information about', example='Acidibacillus ferrooxidans')
    genomes: List[SpeciesClusterGenome]
    d: str = Field(..., description='domain', example='Bacteria')
    p: str = Field(..., description='phylum', example='Proteobacteria')
    c: str = Field(..., description='class', example='Gammaproteobacteria')
    o: str = Field(..., description='order', example='Enterobacterales')
    f: str = Field(..., description='family', example='Enterobacteriaceae')
    g: str = Field(..., description='genus', example='Escherichia')
    s: str = Field(..., description='species', example='Escherichia coli')

#
# class SpeciesHeatmap(BaseModel):
#     name: str = Field(..., description='species to display information about', example='Acidibacillus ferrooxidans')
#     gtdbRep: str = Field(...)
#     xLabels: List[str] = Field(..., description='x labels')
#     yLabels: List[str] = Field(..., description='y labels')
#     data: List[Tuple[str, str, float, int, int]] = Field(..., description='heatmap data')
