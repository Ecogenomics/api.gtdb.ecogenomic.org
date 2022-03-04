from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from api.controller.sankey import get_search_sankey
from api.db import get_gtdb_web_db
from api.model.sankey import SankeySearchRequest, SankeySearchResponse

router = APIRouter(prefix='/sankey', tags=['sankey'])


@router.get('', response_model=SankeySearchResponse,
            summary='Create a sankey diagram for the given parameters.')
def taxonomy_count(taxon: str, releaseFrom: str, releaseTo: str,
                   filterRank: Optional[str] = None, db: Session = Depends(get_gtdb_web_db)):
    request = SankeySearchRequest(taxon=taxon,
                                  releaseFrom=releaseFrom,
                                  releaseTo=releaseTo,
                                  filterRank=filterRank)
    return get_search_sankey(request, db)
