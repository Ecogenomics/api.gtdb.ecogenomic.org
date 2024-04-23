from typing import Literal, List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends, Query
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.controller.taxonomy import post_taxonomy_count, taxonomy_count_rows_to_sv, taxonomy_partial_search, \
    taxa_not_in_lit, taxonomy_partial_search_all_releases
from api.db import get_gtdb_db, get_gtdb_web_db
from api.model.taxonomy import TaxonomyCountRequest, TaxonomyCountResponse, TaxaNotInLiterature, TaxonomyOptional, \
    TaxonomyOptionalRelease
from api.util.cache import cached
from api.util.io import rows_to_delim

router = APIRouter(prefix='/taxonomy', tags=['taxonomy'])


@router.get('/count', response_model=TaxonomyCountResponse,
            summary='Return the count of genomes in all species clusters.')
def taxonomy_count(page: Optional[int] = None,
                   items_per_page: Optional[int] = Query(None, alias='items-per-page'),
                   sort_by: Optional[str] = Query(None, alias='sort-by'),
                   sort_desc: Optional[str] = Query(None, alias='sort-desc'),
                   search: Optional[str] = None,
                   proposed: Optional[bool] = Query(None, alias='gtdb-proposed'),
                   filter_domain: Optional[str] = Query(None, alias='filter-domain'),
                   filter_phylum: Optional[str] = Query(None, alias='filter-phylum'),
                   filter_class: Optional[str] = Query(None, alias='filter-class'),
                   filter_order: Optional[str] = Query(None, alias='filter-order'),
                   filter_family: Optional[str] = Query(None, alias='filter-family'),
                   filter_genus: Optional[str] = Query(None, alias='filter-genus'),
                   filter_species: Optional[str] = Query(None, alias='filter-species'),
                   db_gtdb: Session = Depends(get_gtdb_db),
                   db_web: Session = Depends(get_gtdb_web_db)):
    request = TaxonomyCountRequest(page=page,
                                   itemsPerPage=items_per_page,
                                   sortBy=[x for x in sort_by.split(',')] if sort_by else None,
                                   sortDesc=[x == 'true' for x in sort_desc.split(',')] if sort_desc else None,
                                   search=search,
                                   proposed=proposed,
                                   filterDomain=filter_domain,
                                   filterPhylum=filter_phylum,
                                   filterClass=filter_class,
                                   filterOrder=filter_order,
                                   filterFamily=filter_family,
                                   filterGenus=filter_genus,
                                   filterSpecies=filter_species)
    return post_taxonomy_count(request, db_gtdb, db_web)


@router.get('/count/{fmt}', response_class=StreamingResponse,
            summary='Download the count of genomes in all species clusters.')
def taxonomy_count_download(fmt: Literal['csv', 'tsv'],
                            page: Optional[int] = None,
                            items_per_page: Optional[int] = Query(None, alias='items-per-page'),
                            sort_by: Optional[str] = Query(None, alias='sort-by'),
                            sort_desc: Optional[str] = Query(None, alias='sort-desc'),
                            search: Optional[str] = None,
                            proposed: Optional[bool] = Query(None, alias='gtdb-proposed'),
                            db_gtdb: Session = Depends(get_gtdb_db),
                            db_web: Session = Depends(get_gtdb_web_db)):
    request = TaxonomyCountRequest(page=page,
                                   itemsPerPage=items_per_page,
                                   sortBy=[x for x in sort_by.split(',')] if sort_by else None,
                                   sortDesc=[x == 'true' for x in sort_desc.split(',')] if sort_desc else None,
                                   proposed=proposed,
                                   search=search)

    # Remove pagination to return the full set of data
    request.itemsPerPage = None
    request.page = None

    # Transform into rows
    rows = taxonomy_count_rows_to_sv(post_taxonomy_count(request, db_gtdb, db_web))
    stream = rows_to_delim(rows, delim=',' if fmt == 'csv' else '\t')
    response = StreamingResponse(iter([stream]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-taxonomy-table.{fmt}"
    return response


@router.get(
    '/not-in-literature',
    response_model=List[TaxaNotInLiterature],
    summary='Returns a list of all GTDB proposed taxa.'
)
async def get_taxon_not_in_literature(
        request: Request,
        response: Response,
        db: Session = Depends(get_gtdb_web_db)
):
    return taxa_not_in_lit(db)


# new below

@router.get(
    '/partial/{taxon}',
    response_model=TaxonomyOptional,
    summary='Find the partial taxonomy given a taxon.'
)
# @cached(ttl=-1, disk=True)
async def partial_taxon_search(
        taxon: str,
        request: Request,
        response: Response,
        db: Session = Depends(get_gtdb_db),
):
    return taxonomy_partial_search(taxon, db)


@router.get(
    '/partial/{taxon}/all-releases',
    response_model=List[TaxonomyOptionalRelease],
    summary='Find the partial taxonomy given a taxon across all releases (including NCBI).'
)
# @cached(ttl=-1, disk=True)
async def v_partial_taxon_all_releases(
        taxon: str,
        request: Request,
        response: Response,
        db: Session = Depends(get_gtdb_web_db)
):
    return taxonomy_partial_search_all_releases(taxon, db)
