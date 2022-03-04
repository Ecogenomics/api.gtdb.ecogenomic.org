from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchColumnEnum(Enum):
    ALL = 'all'
    GTDB_TAX = 'gtdb_tax'
    NCBI_TAX = 'ncbi_tax'
    NCBI_ORG_NAME = 'ncbi_org'
    NCBI_GENOME_ID = 'ncbi_id'


class SearchGtdbRequest(BaseModel):
    page: Optional[int] = Field(None, description='page number', example=1)
    itemsPerPage: Optional[int] = Field(None, description='number of items per page', example=10)
    sortBy: Optional[List[str]] = Field(None, description='sort by', example=['d', 'p'])
    sortDesc: Optional[List[bool]] = Field(None, description='sort descending', example=[True, False])
    search: Optional[str] = Field(None, description='main search query', example='Escherichia')
    searchField: Optional[SearchColumnEnum] = Field(None, description='search field', example='name')

    filterText: Optional[str] = Field(None, description='filter across columns')
    gtdbSpeciesRepOnly: Optional[bool] = Field(None, description='only search species representatives', example=True)
    ncbiTypeMaterialOnly: Optional[bool] = Field(None, description='only search type material', example=True)


class SearchGtdbRow(BaseModel):
    gid: str = Field(...)
    accession: str = Field(..., description='accession number', example='GCF_000005845.1')
    ncbiOrgName: str = Field(..., description='NCBI organism name', example='Escherichia coli')
    ncbiTaxonomy: str = Field(..., description='NCBI taxonomy')
    gtdbTaxonomy: str = Field(..., description='GTDB taxonomy')
    isGtdbSpeciesRep: bool = Field(..., )
    isNcbiTypeMaterial: bool = Field(..., )


class SearchGtdbResponse(BaseModel):
    rows: List[SearchGtdbRow]
    totalRows: int
