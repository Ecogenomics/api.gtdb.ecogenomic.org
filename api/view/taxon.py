from typing import List, Optional

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from api.controller.taxon import get_taxon_descendants, search_for_taxon, results_from_previous_releases, \
    search_for_taxon_all_releases, get_taxon_genomes_in_taxon, get_gc_content_histogram_bins, get_taxon_card, \
    get_taxon_genomes_detail
from api.db import get_gtdb_db, get_gtdb_web_db
from api.model.graph import GraphHistogramBin
from api.model.taxon import TaxonDescendants, TaxonSearchResponse, TaxonPreviousReleases, TaxonCard, \
    TaxonPreviousReleasesPaginated, TaxonGenomesDetailResponse

router = APIRouter(prefix='/taxon', tags=['taxon'])


@router.get('/{name}', response_model=List[TaxonDescendants],
            summary='Return the direct descendants of this taxon.')
def taxonomy_count(name: str, db: Session = Depends(get_gtdb_web_db)):
    return get_taxon_descendants(name, db)


@router.get('/search/{taxon}', response_model=TaxonSearchResponse,
            summary='Search for a taxon in the current release, returning partial matches.')
def taxonomy_search(taxon: str, limit: Optional[int] = 100, db: Session = Depends(get_gtdb_db)):
    return search_for_taxon(taxon, limit, db)


@router.get('/search/{taxon}/all-releases', response_model=TaxonSearchResponse,
            summary='Search for a taxon across all releases (including NCBI), returning partial matches.')
def taxonomy_search(taxon: str, limit: Optional[int] = 100, db: Session = Depends(get_gtdb_web_db)):
    return search_for_taxon_all_releases(taxon, limit, db)


@router.get('/{taxon}/genomes', response_model=List[str])
def v_taxon_genomes(taxon: str, sp_reps_only: Optional[bool] = False, db: Session = Depends(get_gtdb_db)):
    return get_taxon_genomes_in_taxon(taxon, sp_reps_only, db)


@router.get('/{taxon}/previous-releases', response_model=List[TaxonPreviousReleases],
            summary='Search for a taxon by name.')
def get_taxon_previous_releases(
        taxon: str, db: Session = Depends(get_gtdb_web_db)
):
    resp = results_from_previous_releases(taxon, db)
    return resp.rows


@router.get('/{taxon}/previous-releases/paginated', response_model=TaxonPreviousReleasesPaginated,
            summary='Search for a taxon by name (paginated).')
def get_taxon_previous_releases_paginated(
        taxon: str,
        page: Optional[int] = 1,
        itemsPerPage: Optional[int] = 10,
        db: Session = Depends(get_gtdb_web_db)
):
    return results_from_previous_releases(taxon, db, page, itemsPerPage)


@router.get('/{taxon}/gc-histogram-bins', response_model=List[GraphHistogramBin],
            summary='Return the bins for plotting GC% content in a histogram.')
def v_get_taxon_gc_histogram_bins(taxon: str, db: Session = Depends(get_gtdb_db)):
    return get_gc_content_histogram_bins(taxon, db)


@router.get('/{taxon}/card', response_model=TaxonCard, summary='Return information about a taxon for the card page.')
def v_get_taxon_card(taxon: str, db_gtdb: Session = Depends(get_gtdb_db), db_web: Session = Depends(get_gtdb_web_db)):
    return get_taxon_card(taxon, db_gtdb, db_web)


@router.get('/{taxon}/genomes-detail', response_model=TaxonGenomesDetailResponse)
def v_get_taxon_genomes_detail(taxon: str, db: Session = Depends(get_gtdb_db)):
    return get_taxon_genomes_detail(taxon, db)
