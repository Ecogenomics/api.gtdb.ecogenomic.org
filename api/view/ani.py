import json
from typing import List, Annotated

from fastapi import APIRouter
from fastapi import Depends, UploadFile, Form, File
from fastapi.responses import Response
from sqlmodel import Session

from api.controller.ani import ani_validate_genomes, ani_create_job, get_ani_job_progress
from api.db import get_gtdb_db, get_gtdb_common_db, GtdbCommonDbDep
from api.model.ani import AniGenomeValidationResponse, AniGenomeValidationRequest, \
    AniJobResultResponseIndex, AniCreateJobResponse, \
    AniConfigResponse, AniJobRequest

router = APIRouter(prefix='/ani', tags=['ani'])


@router.get(
    '/config',
    response_model=AniConfigResponse,
    summary='Retrieve the server side configuration for ANI jobs.'
)
def v_get_ani_config():
    return AniConfigResponse


@router.post("/validate/genomes", response_model=List[AniGenomeValidationResponse],
             summary='Validate the genomes are present in the database.')
def v_ani_validate_genomes(request: AniGenomeValidationRequest, db_gtdb: Session = Depends(get_gtdb_db),
                           db_ani: Session = Depends(get_gtdb_common_db)):
    return ani_validate_genomes(request, db_gtdb, db_ani)


@router.post("/job",
             response_model=AniCreateJobResponse,
             summary='Create a new ANI job.'
             )
async def v_post_ani_create_job(
        job_request: AniJobRequest,
        db: GtdbCommonDbDep
):
    return await ani_create_job(request=job_request, uploaded_files=None, db=db)


@router.put(
    "/job",
    response_model=AniCreateJobResponse,
    summary='Create a new ANI job (with file upload).'
)
async def v_put_ani_create_job(
        payload: Annotated[str, Form()],
        files: Annotated[List[UploadFile], File()],
        db: GtdbCommonDbDep
):
    json_payload = json.loads(payload)
    json_payload['userGenomes']['files'] = [x.filename for x in files]
    job_request = AniJobRequest(**json_payload)
    return await ani_create_job(request=job_request, uploaded_files=files, db=db)


@router.get('/job/{job_id}', response_model=AniJobResultResponseIndex, summary='Retrieve the result of a ANI job.')
def get_by_id(
        job_id: str,
        response: Response,
        db_common: Session = Depends(get_gtdb_common_db),
        db_gtdb: Session = Depends(get_gtdb_db)
):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return get_ani_job_progress(job_id, db_common, db_gtdb)

# @router.get('/{job_id}/table', response_model=AniTableResult, summary='Retrieve the result of a ANI job.')
# def get_by_id(
#         job_id: int,
#         response: Response,
#         db: Session = Depends(get_gtdb_common_db)
# ):
#     response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
#     return get_ani_job_progress(job_id, db)
