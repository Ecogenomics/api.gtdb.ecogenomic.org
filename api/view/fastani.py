from typing import Literal, List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from api.controller.fastani import enqueue_fastani, get_fastani_job_progress, fastani_job_to_rows, get_fastani_config, \
    fastani_heatmap, get_fastani_job_info, fastani_validate_genomes, get_fastani_job_metadata, \
    get_fastani_job_metadata_control
from api.db import get_gtdb_db, get_gtdb_fastani_db
from api.model.fastani import FastAniJobResult, FastAniJobRequest, FastAniConfig, FastAniJobHeatmap, FastAniJobInfo, \
    FastAniJobStatus, FastAniGenomeValidationResponse, FastAniGenomeValidationRequest, FastAniJobMetadata
from api.util.io import rows_to_delim

router = APIRouter(prefix='/fastani', tags=['fastani'])


@router.post("", response_model=FastAniJobResult, summary='Create a new FastANI job.')
async def fastani_view(job_request: FastAniJobRequest, db: Session = Depends(get_gtdb_fastani_db)):
    return enqueue_fastani(job_request, db)


@router.get('/config', response_model=FastAniConfig,
            summary='Retrieve the server-configured parameters for FastANI.')
async def get_config():
    return get_fastani_config()


@router.get('/{job_id}', response_model=FastAniJobResult,
            summary='Retrieve the result of a FastANI job.')
async def get_by_id(
        job_id: int,
        response: Response,
        rows: Optional[int] = None,
        page: Optional[int] = None,
        sortBy: Optional[str] = None,
        sortDesc: Optional[str] = None,
        db: Session = Depends(get_gtdb_fastani_db)
):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    sort_by = sortBy.split(',') if sortBy is not None else None
    sort_desc = [x == 'true' for x in sortDesc.split(',')] if sortDesc is not None else None
    return get_fastani_job_progress(job_id, rows, page, sort_by, sort_desc, db)


@router.get('/{job_id}', response_model=FastAniJobResult,
            summary='Retrieve the result of a FastANI job.')
async def get_by_id(
        job_id: int,
        response: Response,
        rows: Optional[int] = None,
        page: Optional[int] = None,
        sortBy: Optional[str] = None,
        sortDesc: Optional[str] = None,
        db: Session = Depends(get_gtdb_fastani_db)
):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    sort_by = sortBy.split(',') if sortBy is not None else None
    sort_desc = [x == 'true' for x in sortDesc.split(',')] if sortDesc is not None else None
    return get_fastani_job_progress(job_id, rows, page, sort_by, sort_desc, db)


@router.get('/{job_id}/heatmap/{method}', response_model=FastAniJobHeatmap)
async def get_job_id_heatmap(
        job_id: int,
        method: Literal['ani', 'af'],
        response: Response,
                             db_gtdb: Session = Depends(get_gtdb_db),
        db_fastani: Session = Depends(get_gtdb_fastani_db)
):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return fastani_heatmap(job_id, method, db_gtdb, db_fastani)



@router.get('/{job_id}/metadata', response_model=FastAniJobMetadata)
async def v_get_job_id_metadata(
        job_id: int,
        db_gtdb: Session = Depends(get_gtdb_db),
        db_fastani: Session = Depends(get_gtdb_fastani_db),
):
    return get_fastani_job_metadata_control(job_id, db_gtdb, db_fastani)


@router.get('/{job_id}/info', response_model=FastAniJobInfo, summary='Retrieve information about a FastANI job.')
async def v_job_id_info(
        job_id: int,
        response: Response,
        db: Session = Depends(get_gtdb_fastani_db)
):
    result = get_fastani_job_info(job_id, db)
    if result and (result.status is FastAniJobStatus.FINISHED or result.status is FastAniJobStatus.ERROR):
        pass
    else:
        response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return result


@router.get('/{job_id}/{fmt}', response_class=StreamingResponse,
            summary='Download the result of a FastANI job in delimited format.')
async def get_by_id_download(job_id: int, fmt: Literal['csv', 'tsv'],   db: Session = Depends(get_gtdb_fastani_db)):
    rows = fastani_job_to_rows(job_id, db)
    stream = rows_to_delim(rows, delim=',' if fmt == 'csv' else '\t')
    response = StreamingResponse(iter([stream]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-fastani-{job_id}.{fmt}"
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return response

@router.post("/validate/genomes", response_model=List[FastAniGenomeValidationResponse], summary='Validate the genomes are present in the database.')
async def v_fastani_validate_genomes(request: FastAniGenomeValidationRequest, db_gtdb: Session = Depends(get_gtdb_db), db_fastani: Session = Depends(get_gtdb_fastani_db)):
    return fastani_validate_genomes(request, db_gtdb, db_fastani)
