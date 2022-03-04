from typing import List, Optional

from pydantic import BaseModel, Field


class SankeySearchRequest(BaseModel):
    releaseFrom: str = Field(..., description='the release to search from', example='R80')
    releaseTo: str = Field(..., description='the release to search to', example='R80')
    taxon: str = Field(..., description='the taxon to search', example='d__Bacteria')
    filterRank: Optional[str] = Field(None, description='filter the results to this subset of results', example='o__')

class SankeyNode(BaseModel):
    col: str
    id: int
    linkHighlightId: List[int]
    name: str
    nodeHighlightId: List[int]
    total: int

class SankeyLink(BaseModel):
    id: int
    linkHighlightId: List[int]
    nodeHighlightId: List[int]
    source: int
    target: int
    value: int

class SankeySearchResponse(BaseModel):
    nodes: List[SankeyNode]
    links: List[SankeyLink]
