from typing import List, Optional

from pydantic import BaseModel, Field


class TaxonomyCount(BaseModel):
    """The response returned from the species cluster endpoint."""
    d: str = Field(..., description='domain', example='Bacteria')
    p: str = Field(..., description='phylum', example='Proteobacteria')
    c: str = Field(..., description='class', example='Gammaproteobacteria')
    o: str = Field(..., description='order', example='Enterobacterales')
    f: str = Field(..., description='family', example='Enterobacteriaceae')
    g: str = Field(..., description='genus', example='Escherichia')
    s: str = Field(..., description='species', example='Escherichia coli')
    count: int = Field(..., description='number of genomes in the species cluster', example=4370)


class TaxonomyCountResponse(BaseModel):
    """The response returned from the species cluster endpoint."""
    totalRows: int = Field(..., description='total number of rows in the query', example=1000)
    rows: List[TaxonomyCount] = Field(..., description='list of taxonomy counts')


class TaxonomyCountRequest(BaseModel):
    """The request send to the species cluster endpoint."""
    page: Optional[int] = Field(None, description='page number', example=1)
    itemsPerPage: Optional[int] = Field(None, description='number of items per page', example=10)
    sortBy: Optional[List[str]] = Field(None, description='sort by', example=['d', 'p'])
    sortDesc: Optional[List[bool]] = Field(None, description='sort descending', example=[True, False])
    search: Optional[str] = Field(None, description='search string across all columns and rows', example='Escherichia')
    proposed: Optional[bool] = Field(None, description='show only GTDB proposed names')

    filterDomain: Optional[str] = Field(None, description='Filter by domains that contain this value')
    filterPhylum: Optional[str] = Field(None, description='Filter by phyla that contain this value')
    filterClass: Optional[str] = Field(None, description='Filter by classes that contain this value')
    filterOrder: Optional[str] = Field(None, description='Filter by orders that contain this value')
    filterFamily: Optional[str] = Field(None, description='Filter by families that contain this value')
    filterGenus: Optional[str] = Field(None, description='Filter by genera that contain this value')
    filterSpecies: Optional[str] = Field(None, description='Filter by species that contain this value')


# new below

class TaxonomyRequired(BaseModel):
    """The required full seven taxonomy without taxon prefix."""
    d: str = Field(..., title='Domain', example='Bacteria')
    p: str = Field(..., title='Phylum', example='Proteobacteria')
    c: str = Field(..., title='Class', example='Gammaproteobacteria')
    o: str = Field(..., title='Order', example='Enterobacterales')
    f: str = Field(..., title='Family', example='Enterobacteriaceae')
    g: str = Field(..., title='Genus', example='Salmonella')
    s: str = Field(..., title='Species', example='Salmonella enterica')


class TaxonomyOptional(BaseModel):
    """The optional full seven taxonomy without taxon prefix."""
    d: Optional[str] = Field(None, title='Domain', example='Bacteria')
    p: Optional[str] = Field(None, title='Phylum', example='Proteobacteria')
    c: Optional[str] = Field(None, title='Class', example='Gammaproteobacteria')
    o: Optional[str] = Field(None, title='Order', example='Enterobacterales')
    f: Optional[str] = Field(None, title='Family', example='Enterobacteriaceae')
    g: Optional[str] = Field(None, title='Genus', example='Salmonella')
    s: Optional[str] = Field(None, title='Species', example='Salmonella enterica')


class TaxaNotInLiterature(BaseModel):
    """Information about GTDB proposed taxa that are not in literature."""
    taxon: str = Field(..., title='Taxon', example='Foo Bar')
    taxonomy: TaxonomyOptional = Field(..., title='Taxonomy')
    appearedInRelease: str = Field(..., title='Appeared in release', example='86.2')
    taxonStatus: str = Field(..., title='Taxon status', example='GTDB correction of existing name')
    notes: str = Field(..., title='Notes', example='original name: Candidatus Foo Bar et al. 2015')

class TaxonomyOptionalRelease(BaseModel):
    release: str = Field(..., title='Release', example='R86.2')
    taxonomy: TaxonomyOptional = Field(..., title='Taxonomy in this release')
