from typing import List, Optional

from pydantic import BaseModel, Field


class TaxonDescendants(BaseModel):
    """The response returned from the species cluster endpoint."""
    taxon: str = Field(..., description='the name of this taxon', example='d__Archaea')
    total: int = Field(..., description='the total number of genomes in GTDB with this taxon', example=4316)
    nDescChildren: Optional[int] = Field(None, description='the total number of immediate descendant taxa', example=4316)
    isGenome: Optional[bool] = Field(None)
    isRep: Optional[bool] = Field(None)
    typeMaterial: Optional[str] = Field(None)
    bergeysUrl: Optional[str] = Field(None)
    seqcodeUrl: Optional[str] = Field(None)
    lpsnUrl: Optional[str] = Field(None)


class TaxonSearchResponse(BaseModel):
    matches: List[str] = Field(..., description='a collection of matches to the search string',
                               example=['d__Archaea', 'd__Bacteria'])


class TaxonPreviousReleases(BaseModel):
    taxon: str = Field(..., description='the name of this taxon', example='d__Archaea')
    firstSeen: str = Field(..., description='the first release this taxon was seen in', example='R80')
    lastSeen: str = Field(..., description='the last release this taxon was seen in', example='R95')

class TaxonPreviousReleasesPaginated(BaseModel):
    totalRows: int = Field(..., description='the total number of previous releases for this taxon', example=1234)
    rows: List[TaxonPreviousReleases] = Field(..., description='a collection of previous releases for this taxon')



class TaxonCard(BaseModel):
    nGenomes: int = Field(..., description='the number of genomes in this taxon', example=1234)
    rank: str = Field(..., description='the rank of this taxon', example='domain')
    inReleases: List[str] = Field(..., description='a list of releases this taxon has appeared in (sorted)', example='[R80, R95]')
    higherRanks: List[str] = Field(..., description='a list of higher ranks for this taxon')
