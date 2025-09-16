import json
from typing import Annotated, List, Literal

from fastapi import APIRouter, File, Form, Path, UploadFile, Query
from fastapi.responses import Response

from api.controller.skani import (
    ani_validate_genomes, get_job_data_index_page, get_job_data_table_page,
    get_job_id_status, skani_create_job, skani_get_heatmap
)
from api.db import GtdbCommonDbDep, GtdbDbDep
from api.model.skani import (
    SkaniCreatedJobResponse, SkaniJobDataHeatmapResponse, SkaniJobDataIndexResponse, SkaniJobDataTableResponse,
    SkaniJobRequest,
    SkaniJobStatusResponse, SkaniJobUploadMetadata, SkaniServerConfig,
    SkaniValidateGenomesRequest, SkaniValidateGenomesResponse
)

router = APIRouter(prefix='/skani', tags=['skani'])


@router.get(
    '/config',
    response_model=SkaniServerConfig,
    summary='Retrieve the server side configuration for ANI jobs.'
)
def v_get_ani_config():
    return SkaniServerConfig


@router.post(
    "/job",
    response_model=SkaniCreatedJobResponse,
    summary='Create a new skani job.'
)
async def v_post_ani_create_job(
        job_request: SkaniJobRequest,
        db: GtdbCommonDbDep
):
    return await skani_create_job(request=job_request, uploaded_files=None, upload_metadata=None, db=db)


@router.put(
    "/job",
    response_model=SkaniCreatedJobResponse,
    summary='Create a new skani job (with file upload).'
)
async def v_put_ani_create_job(
        payload: Annotated[str, Form()],
        files: Annotated[List[UploadFile], File()],
        uploadMetadata: Annotated[str, Form()],
        db: GtdbCommonDbDep
):
    upload_metadata = SkaniJobUploadMetadata(**json.loads(uploadMetadata))
    job_request = SkaniJobRequest(**json.loads(payload))
    return await skani_create_job(request=job_request, uploaded_files=files, upload_metadata=upload_metadata, db=db)


@router.post(
    "/validate/genomes",
    response_model=list[SkaniValidateGenomesResponse],
    summary='Validate the genomes are present in the ANI database.'
)
def v_ani_validate_genomes(
        request: SkaniValidateGenomesRequest,
        db_gtdb: GtdbDbDep,
        db_ani: GtdbCommonDbDep
):
    return ani_validate_genomes(request, db_gtdb, db_ani)


@router.get(
    "/job/{jobId}/query",
    response_model=SkaniJobDataIndexResponse,
    summary='Retrieve information about a specific job for the query page.'
)
def v_skani_get_job_id(
        jobId: Annotated[str, Path(
            ...,
            max_length=8,
            description='The job id to search.',
            example='40faf0c0',
        )],
        db_gtdb: GtdbDbDep,
        db_common: GtdbCommonDbDep
):
    return get_job_data_index_page(jobId, db_gtdb, db_common)


@router.get(
    "/job/{jobId}/table",
    response_model=SkaniJobDataTableResponse,
    summary='Retrieve information about a specific job for the table page.'
)
def v_skani_get_job_id_table(
        jobId: Annotated[str, Path(
            ...,
            max_length=8,
            description='The job id to search.',
            example='40faf0c0',
        )],
        db_common: GtdbCommonDbDep,
        response: Response,
        showNa: Annotated[bool, Query(
            description='If no-hits (distant) should be shown.',
        )] = False,
):
    # # Parse the sort_by and sort_desc parameters into lists
    # if sort_by is not None:
    #     sort_by = [x.strip() for x in sort_by.split(',')]
    # if sort_desc is not None:
    #     sort_desc = [x.strip().lower() == 'true' for x in sort_desc.split(',')]

    data = get_job_data_table_page(jobId, showNa, db_common)
    if data.completed is not True:
        # Add this header if the job is still processing
        response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return data



@router.get(
    "/job/{jobId}/status",
    response_model=SkaniJobStatusResponse,
    summary='Retrieve progress information about a specific job.'
)
def v_skani_get_job_id_status(
        jobId: Annotated[str, Path(
            ...,
            max_length=8,
            description='The job id to search.',
            example='40faf0c0',
        )],
        db_common: GtdbCommonDbDep,
        response: Response,
):
    data = get_job_id_status(jobId, db_common)
    if data.completedEpoch is None:
        # Add this header if the job is still processing
        response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return data



@router.get(
    '/job/{job_id}/heatmap',
    response_model=SkaniJobDataHeatmapResponse,
    summary='Retrieve the heatmap data for a specific job.'
)
def v_get_job_id_heatmap(
        job_id: Annotated[str, Path(
            ...,
            max_length=8,
            description='The job id to search.',
            example='3d015dc2',
        )],
        response: Response,
        db_gtdb: GtdbDbDep,
        db_common: GtdbCommonDbDep,
        clusterBy: Annotated[Literal['af', 'ani'], Query(
            description='Cluster the heatmap by either average nucleotide identity (ani) or alignment fraction (af).',
            example='ani',
        )] = 'ani',
):
    data = skani_get_heatmap(job_id, clusterBy, db_gtdb, db_common)
    if not data.completed:
        response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return data
