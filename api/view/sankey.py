from typing import Annotated

from fastapi import APIRouter, Query

from api.controller.sankey import get_search_sankey
from api.db import GtdbWebDbDep
from api.model.sankey import SankeySearchRequest, SankeySearchResponse

router = APIRouter(prefix='/sankey', tags=['sankey'])


@router.get(
    '',
    response_model=SankeySearchResponse,
    summary='Create a sankey diagram for the given parameters.'
)
def taxonomy_count(
        taxon: Annotated[str, Query(
            ...,
            description='The GTDB taxon to search.',
            example='g__Pelagimonas',
            regex=r'^[dpcofgs]__.+$'
        )],
        releaseFrom: Annotated[str, Query(
            ...,
            description='The release to search from (inclusive).',
            example='R80',
        )],
        releaseTo: Annotated[str, Query(
            ...,
            description='The release to search to (inclusive).',
            example='R226',
        )],
        db: GtdbWebDbDep,
        filterRank: Annotated[str | None, Query(
            description='Filter the results to this subset of results.',
            example='o__',
            regex=r'^[dpcofgs]__$'
        )] = None
):
    request = SankeySearchRequest(
        taxon=taxon,
        releaseFrom=releaseFrom,
        releaseTo=releaseTo,
        filterRank=filterRank
    )
    return get_search_sankey(request, db)
