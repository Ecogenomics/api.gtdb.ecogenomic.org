from typing import List
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.controller.advanced import get_advanced_search_options, get_advanced_search_operators, \
    get_advanced_search_columns, get_advanced_search, adv_search_query_to_rows
from api.db import get_gtdb_db
from api.model.advanced import AdvancedSearchOptionsResponse, AdvancedSearchOperatorResponse, \
    AdvancedSearchColumnResponse, AdvancedSearchResult
from api.util.io import rows_to_delim

router = APIRouter(prefix='/advanced', tags=['advanced'])


@router.get('/options', response_model=List[AdvancedSearchOptionsResponse],
            summary='Return a list of all valid options in the advanced search.')
def v_advanced_get_options():
    return get_advanced_search_options()


@router.get('/operators', response_model=List[AdvancedSearchOperatorResponse],
            summary='Return a list of all valid operators in the advanced search.')
def v_advanced_get_operators():
    return get_advanced_search_operators()


@router.get('/columns', response_model=List[AdvancedSearchColumnResponse],
            summary='Return a list of all valid columns in the advanced search.')
def v_advanced_get_columns():
    return get_advanced_search_columns()


@router.get('/search', response_model=AdvancedSearchResult,
            summary='Return the result of an advanced search query.')
def v_advanced_get_search(request: Request, db: Session = Depends(get_gtdb_db)):
    return get_advanced_search(query=dict(request.query_params), db=db)


@router.get('/search/download/{fmt}', response_class=StreamingResponse,
            summary='Download the result of a Advanced Search query in delimited format.')
def get_by_id_download(fmt: Literal['csv', 'tsv'], request: Request, db: Session = Depends(get_gtdb_db)):
    adv_result = get_advanced_search(query=dict(request.query_params), db=db)
    rows = adv_search_query_to_rows(adv_result)
    stream = rows_to_delim(rows, delim=',' if fmt == 'csv' else '\t')
    response = StreamingResponse(iter([stream]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-adv-search.{fmt}"
    return response


@router.get('/search/download-genomes', response_class=StreamingResponse, summary='Download a shell script to download genomes from Advanced Search results.')
def v_download_genomes_from_adv(
        method: Literal['datasets', 'curl'], request: Request, db: Session = Depends(get_gtdb_db),
        gff: bool = False, rna: bool = False, cds: bool = False, protein: bool = False, genome: bool = True,
        seqReport: bool = False
):
    adv_result = get_advanced_search(query=dict(request.query_params), db=db)
    gids = {x['organism_name'] for x in adv_result.rows}

    options = list()
    if gff:
        options.append('gff3' if method == 'datasets' else 'GENOME_GFF')
    if rna:
        options.append('rna' if method == 'datasets' else 'RNA_FASTA')
    if cds:
        options.append('cds' if method == 'datasets' else 'CDS_FASTA')
    if protein:
        options.append('protein' if method == 'datasets' else 'PROT_FASTA')
    if genome:
        options.append('genome' if method == 'datasets' else 'GENOME_FASTA')
    if seqReport:
        options.append('seq-report' if method == 'datasets' else 'SEQUENCE_REPORT')

    lines = ['#!/bin/bash']
    for gid in gids:
        if method == 'datasets':
            lines.append(f'datasets download genome accession {gid} --include {",".join(options)} --filename {gid}.zip')
        else:
            lines.append(f'curl -OJX GET "https://api.ncbi.nlm.nih.gov/datasets/v2alpha/genome/accession/{gid}/download?include_annotation_type={",".join(options)}&filename={gid}.zip" -H "Accept: application/zip"')

    stream = '\n'.join(lines) + '\n'
    response = StreamingResponse(iter([stream]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-adv-search-genomes.sh"
    return response
