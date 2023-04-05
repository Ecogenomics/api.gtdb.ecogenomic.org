from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from api.controller.fastani import enqueue_fastani, get_fastani_job_progress, fastani_job_to_rows, get_fastani_config, \
    fastani_heatmap, get_fastani_job_info
from api.db import get_gtdb_db, get_gtdb_common_db
from api.model.fastani import FastAniJobResult, FastAniJobRequest, FastAniConfig, FastAniJobHeatmap, FastAniJobInfo, \
    FastAniJobStatus
from api.util.io import rows_to_delim

router = APIRouter(prefix='/fastani', tags=['fastani'])


@router.post("", response_model=FastAniJobResult, summary='Create a new FastANI job.')
async def fastani_view(job_request: FastAniJobRequest, db: Session= Depends(get_gtdb_common_db)):
    return enqueue_fastani(job_request, db)


@router.get('/config', response_model=FastAniConfig,
            summary='Retrieve the server-configured parameters for FastANI.')
async def get_config():
    return get_fastani_config()


@router.get('/{job_id}', response_model=FastAniJobResult,
            summary='Retrieve the result of a FastANI job.')
async def get_by_id(job_id: str, response: Response, rows: Optional[int] = None,
                    page: Optional[int] = None, sortBy: Optional[str] = None, sortDesc: Optional[str] = None):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    sort_by = sortBy.split(',') if sortBy is not None else None
    sort_desc = [x == 'true' for x in sortDesc.split(',')] if sortDesc is not None else None
    return get_fastani_job_progress(job_id, rows, page, sort_by, sort_desc)


@router.get('/{job_id}/heatmap/{method}', response_model=FastAniJobHeatmap)
async def get_job_id_heatmap(job_id: str, method: Literal['ani', 'af'], response: Response,
                             db: Session = Depends(get_gtdb_db)):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return fastani_heatmap(job_id, method, db)


@router.get('/{job_id}/info', response_model=FastAniJobInfo, summary='Retrieve information about a FastANI job.')
async def v_job_id_info(job_id: str, response: Response):
    result = get_fastani_job_info(job_id)
    if result and (result.status is FastAniJobStatus.FINISHED or result.status is FastAniJobStatus.ERROR):
        pass
    else:
        response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return get_fastani_job_info(job_id)


@router.get('/{job_id}/{fmt}', response_class=StreamingResponse,
            summary='Download the result of a FastANI job in delimited format.')
async def get_by_id_download(job_id: str, fmt: Literal['csv', 'tsv']):
    rows = fastani_job_to_rows(job_id)
    stream = rows_to_delim(rows, delim=',' if fmt == 'csv' else '\t')
    response = StreamingResponse(iter([stream]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-fastani-{job_id}.{fmt}"
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return response

