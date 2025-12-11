from typing import List, Annotated

from fastapi import APIRouter, Path, Query

from api.controller.taxon import get_taxon_descendants, search_for_taxon, results_from_previous_releases, \
    search_for_taxon_all_releases, get_taxon_genomes_in_taxon, get_gc_content_histogram_bins, get_taxon_card, \
    get_taxon_genomes_detail
from api.db import GtdbWebDbDep, GtdbDbDep
from api.exceptions import HttpBadRequest
from api.model.graph import GraphHistogramBin
from api.model.taxon import TaxonDescendants, TaxonSearchResponse, TaxonPreviousReleases, TaxonCard, \
    TaxonPreviousReleasesPaginated, TaxonGenomesDetailResponse

router = APIRouter(prefix='/taxon', tags=['taxon'])


@router.get(
    '/{name}',
    response_model=List[TaxonDescendants],
    summary='Return the direct descendants of this taxon.'
)
def v_get_taxon_name(
        name: Annotated[str, Path(
            ...,
            description='The GTDB taxon to search.',
            example='d__Bacteria',
        )],
        db: GtdbWebDbDep
):
    return get_taxon_descendants(name, db)


@router.get(
    '/search/{taxon}',
    response_model=TaxonSearchResponse,
    summary='Search for a taxon in the current release, returning partial matches.'
)
def v_get_search_taxon(
        taxon: Annotated[str, Path(
            ...,
            description='The partial GTDB taxon to search.',
            example='bac',
        )],
        db: GtdbDbDep,
        limit: Annotated[int | None, Query(
            description='The maximum number of results to return for each rank.',
            example=100,
            ge=1,
            le=100
        )] = 100,
):
    return search_for_taxon(taxon, limit, db)


@router.get(
    '/search/{taxon}/all-releases',
    response_model=TaxonSearchResponse,
    summary='Search for a taxon across all releases (including NCBI), returning partial matches.'
)
def v_get_search_taxon_all_releases(
        taxon: Annotated[str, Path(
            ...,
            description='The partial GTDB taxon to search.',
            example='bac',
        )],
        db: GtdbWebDbDep,
        limit: Annotated[int | None, Query(
            description='The maximum number of results to return for each rank.',
            example=100,
            ge=1,
            le=100
        )] = 100,
):
    return search_for_taxon_all_releases(taxon, limit, db)


@router.get(
    '/{taxon}/genomes',
    response_model=List[str],
    summary='Return the genomes that belong to this taxon (optionally only species representatives).'
)
def v_get_taxon_genomes(
        taxon: Annotated[str, Path(
            ...,
            description='The GTDB taxon to search.',
            example='d__Archaea',
            regex=r'^[dpcofgs]__.+$'
        )],
        db: GtdbDbDep,
        sp_reps_only: Annotated[bool | None, Query(
            description='If true, only return species representatives.',
            example=True,
        )] = False,
):
    return get_taxon_genomes_in_taxon(taxon, sp_reps_only, db)


@router.get(
    '/{taxon}/previous-releases',
    response_model=List[TaxonPreviousReleases],
    summary='Search for a taxon by name across previous releases, returning the releases they were present in.'
)
def v_get_taxon_previous_releases(
        taxon: Annotated[str, Path(
            ...,
            description='The partial GTDB taxon to search.',
            example='bac',
        )],
        db: GtdbWebDbDep
):
    resp = results_from_previous_releases(taxon, db)
    return resp.rows


@router.get(
    '/{taxon}/previous-releases/paginated',
    response_model=TaxonPreviousReleasesPaginated,
    summary='Search for a taxon by name across previous releases, returning the releases they were present in (paginated).'
)
def get_taxon_previous_releases_paginated(
        taxon: Annotated[str, Path(
            ...,
            description='The partial GTDB taxon to search.',
            example='bac',
        )],
        db: GtdbWebDbDep,
        page: Annotated[int | None, Query(
            description='The page number to view.',
            example=1,
        )] = 1,
        itemsPerPage: Annotated[int | None, Query(
            description='The number of results to display per page.',
            example=10,
        )] = 10
):
    return results_from_previous_releases(taxon, db, page, itemsPerPage)


@router.get(
    '/{taxon}/gc-histogram-bins',
    response_model=List[GraphHistogramBin],
    summary='Return the bins for plotting GC% content in a histogram.'
)
def v_get_taxon_gc_histogram_bins(
        taxon: Annotated[str, Path(
            ...,
            description='The GTDB taxon to search.',
            example='d__Archaea',
            regex=r'^[dpcofgs]__.+$'
        )],
        db: GtdbDbDep
):
    return get_gc_content_histogram_bins(taxon, db)


@router.get(
    '/{taxon}/card',
    response_model=TaxonCard,
    summary='Return information about a taxon for the genome page.'
)
def v_get_taxon_card(
        taxon: Annotated[str, Path(
            ...,
            description='The GTDB taxon to search.',
            example='d__Archaea',
            regex=r'^[dpcofgs]__.+$'
        )],
        db_gtdb: GtdbDbDep
):
    return get_taxon_card(taxon, db_gtdb)


@router.get(
    '/{taxon}/genomes-detail',
    response_model=TaxonGenomesDetailResponse,
    summary='Return detailed information about the genomes that belong to this taxon (optionally only species representatives).'
)
def v_get_taxon_genomes_detail(
        taxon: Annotated[str, Path(
            ...,
            description='The GTDB taxon to search.',
            example='d__Archaea',
            regex=r'^[dpcofgs]__.+$'
        )],
        db: GtdbDbDep,
        sp_reps_only: Annotated[bool | None, Query(
            description='If true, only return species representatives.',
            example=True,
        )] = False
):
    return get_taxon_genomes_detail(taxon, sp_reps_only, db)
