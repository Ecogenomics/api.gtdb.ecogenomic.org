from typing import Optional, Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.controller.search import search_gtdb, search_gtdb_to_rows
from api.db import get_gtdb_db
from api.model.search import SearchGtdbRequest, SearchGtdbResponse, SearchColumnEnum
from api.util.io import rows_to_delim

router = APIRouter(prefix='/search', tags=['search'])


@router.get('/gtdb', response_model=SearchGtdbResponse,
            summary='Search for a taxon by name.')
def get_search_gtdb(search: str,
                    page: Optional[int] = 1,
                    itemsPerPage: Optional[int] = 100,
                    sortBy: Optional[str] = None,
                    sortDesc: Optional[str] = None,
                    searchField: Optional[SearchColumnEnum] = SearchColumnEnum.ALL,
                    filterText: Optional[str] = None,
                    gtdbSpeciesRepOnly: Optional[bool] = False,
                    ncbiTypeMaterialOnly: Optional[bool] = False,
                    db: Session = Depends(get_gtdb_db)):
    request = SearchGtdbRequest(search=search,
                                sortBy=sortBy.split(',') if sortBy else None,
                                sortDesc=[x == 'true' for x in sortDesc.split(',')] if sortDesc else None,
                                page=page,
                                itemsPerPage=itemsPerPage,
                                searchField=searchField,
                                filterText=filterText,
                                gtdbSpeciesRepOnly=gtdbSpeciesRepOnly,
                                ncbiTypeMaterialOnly=ncbiTypeMaterialOnly)
    return search_gtdb(request, db)


@router.get('/gtdb/{fmt}', response_class=StreamingResponse,
            summary='Download the results of a GTDB search.')
def get_by_id_download(search: str,
                             fmt: Literal['csv', 'tsv'],
                             sortBy: Optional[str] = None,
                             sortDesc: Optional[str] = None,
                             searchField: Optional[SearchColumnEnum] = SearchColumnEnum.ALL,
                             filterText: Optional[str] = None,
                             gtdbSpeciesRepOnly: Optional[bool] = False,
                             ncbiTypeMaterialOnly: Optional[bool] = False,
                             db: Session = Depends(get_gtdb_db)):
    rows = search_gtdb_to_rows(get_search_gtdb(search, page=None, itemsPerPage=None,
                                               sortBy=sortBy, sortDesc=sortDesc,
                                               searchField=searchField, filterText=filterText,
                                               gtdbSpeciesRepOnly=gtdbSpeciesRepOnly,
                                               ncbiTypeMaterialOnly=ncbiTypeMaterialOnly,
                                               db=db))
    stream = rows_to_delim(rows, delim=',' if fmt == 'csv' else '\t')
    response = StreamingResponse(iter([stream]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-search.{fmt}"
    return response
