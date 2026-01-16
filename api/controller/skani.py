import random
from typing import Collection

import numpy as np
import sqlmodel as sm
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from api.config import (
    ANI_JOB_ID_MAX_VALUE, ANI_MAX_PAIRWISE, ANI_QUEUE_MAX_PENDING_JOBS, ANI_USER_MAX_FILE_COUNT,
    ANI_USER_MAX_FILE_NAME_LENGTH, ANI_USER_MAX_FILE_SIZE_MB_EACH
)
from api.db.common import (
    DbGenomesOnDisk, DbSkaniGenome, DbSkaniJob, DbSkaniJobQuery, DbSkaniJobReference, DbSkaniJobResult, DbSkaniParam,
    DbSkaniUserGenome
)
from api.db.gtdb import DbGenomes, DbMetadataNcbi, DbMetadataTaxonomy
from api.exceptions import HttpBadRequest, HttpInternalServerError, HttpNotFound
from api.model.skani import (
    SkaniCalculationMode, SkaniCreatedJobResponse, SkaniJobDataHeatmapResponse, SkaniJobDataIndexResponse,
    SkaniJobDataTableResponse,
    SkaniJobRequest, SkaniJobStatusResponse, SkaniJobUploadMetadata, SkaniParameters,
    SkaniResultTableRow,
    SkaniValidateGenomesRequest,
    SkaniValidateGenomesResponse, SkaniVersion, UtilSkaniJobResults
)
from api.util.accession import canonical_gid
from api.util.io import read_upload_file_bytes_limit
from api.util.matrix import cluster_matrix


# HELPER METHODS
def generate_random_job_id() -> int:
    return random.randint(0, ANI_JOB_ID_MAX_VALUE)


def generate_random_job_name() -> str:
    return convert_job_id_to_string(generate_random_job_id())


def convert_job_id_to_string(v: int) -> str:
    if v > ANI_JOB_ID_MAX_VALUE:
        raise HttpInternalServerError(f'Unable to process this job id.')
    return f'{v:08x}'


def convert_job_id_to_int(v: str) -> int:
    out = int(v, 16)
    if out > ANI_JOB_ID_MAX_VALUE:
        raise HttpInternalServerError(f'Unable to process this job id.')
    return out


# VIEW METHODS


def get_skani_job_queue_size(db: Session) -> int:
    """Get the current queue size of pending jobs in the ANI database."""
    query = (
        sm.select(sm.func.count())
        .select_from(DbSkaniJob)
        .where(DbSkaniJob.completed == None)
    )
    result = db.exec(query).first()
    return int(result)


async def skani_create_job(
        request: SkaniJobRequest,
        uploaded_files: list[UploadFile] | None,
        upload_metadata: SkaniJobUploadMetadata | None,
        db: Session
) -> SkaniCreatedJobResponse:
    """Enqueue a skani job and return a unique ID to the user."""

    # Depending on the calculation mode, remove the reference list
    if request.calcMode is SkaniCalculationMode.TRIANGLE:
        request.reference = list()

    # TODO: Validate that only alphanumeric characters in the file name?
    ani_user_max_file_size_bytes = ANI_USER_MAX_FILE_SIZE_MB_EACH * 1024 * 1024

    job_queue_size = get_skani_job_queue_size(db)
    if job_queue_size > ANI_QUEUE_MAX_PENDING_JOBS:
        raise HttpBadRequest(
            f'The job queue is full, please try again later. Contact us if this error persists for >24 hours.'
        )

    # Perform validation on input arguments
    request.validate_email()
    request.validate_parameters(request.calcMode)

    # Validate genome rules
    q_genomes, r_genomes = set(request.query), set(request.reference)
    if request.calcMode is SkaniCalculationMode.QVR:
        n_pairwise = len(q_genomes) * len(r_genomes)
    elif request.calcMode is SkaniCalculationMode.TRIANGLE:
        n_pairwise = len(q_genomes) ** 2
    else:
        raise HttpBadRequest(f'The calculation mode must be set.')
    if n_pairwise > ANI_MAX_PAIRWISE:
        raise HttpBadRequest(f'Too many pairwise comparisons: {n_pairwise:,} > {ANI_MAX_PAIRWISE:,}')
    if n_pairwise == 0:
        raise HttpBadRequest(f'No pairwise comparisons requested.')

    # If user files have been uploaded, verify no restrictions are violated
    if uploaded_files is not None and len(uploaded_files) > 0:
        if len(uploaded_files) > ANI_USER_MAX_FILE_COUNT:
            raise HttpBadRequest(
                f'You have exceeded the maximum number of uploaded files ({ANI_USER_MAX_FILE_COUNT:,}).'
            )
        for cur_file in uploaded_files:
            # Check the file name length limit
            if cur_file.filename is None:
                raise HttpBadRequest('One of the uploaded files is missing a filename.')
            else:
                if len(cur_file.filename) > ANI_USER_MAX_FILE_NAME_LENGTH:
                    raise HttpBadRequest(
                        f'{cur_file.filename}: name exceeds the limit of {ANI_USER_MAX_FILE_NAME_LENGTH:,} characters.'
                    )
            # Check the file size
            if cur_file.size is None:
                raise HttpBadRequest('One of the uploaded files is missing a size.')
            else:
                if cur_file.size > ani_user_max_file_size_bytes:
                    raise HttpBadRequest(
                        f'{cur_file.filename} exceeds the maximum file size of {ANI_USER_MAX_FILE_SIZE_MB_EACH:,} MB.'
                    )

    # After validation has completed, read the content of the files (not trusting file size metadata!)
    d_file_content = dict()
    if uploaded_files is not None and len(uploaded_files) > 0:
        for cur_file in uploaded_files:

            # Attempt to read the file
            try:
                d_file_content[cur_file.filename] = await read_upload_file_bytes_limit(
                    cur_file,
                    ani_user_max_file_size_bytes
                )
            except UnicodeDecodeError:
                raise HttpBadRequest(f'Unable to read {cur_file.filename}, not a text file.')
            except Exception:
                raise HttpInternalServerError(f'Unable to read {cur_file.filename}, please try again.')

    # If user genomes have been supplied, then extract their names
    user_genome_ids = set(d_file_content.keys())

    # Deduplicate input genomes
    all_ncbi_genomes = (q_genomes.union(r_genomes)) - user_genome_ids

    # Try and add those genomes into the "genome" mapping table and return their IDs
    genomes_in_db = get_genome_ids_from_ncbi_names(all_ncbi_genomes, db)

    # Remove any NCBI query+reference genomes that aren't in the database
    q_genome_ids = {genomes_in_db[x] for x in q_genomes if genomes_in_db.get(x) is not None}
    r_genome_ids = {genomes_in_db[x] for x in r_genomes if genomes_in_db.get(x) is not None}

    # Validate that there are still results after removing the accessions that dont exist in the db
    n_query_genomes_total = len(q_genome_ids) + len(q_genomes.intersection(user_genome_ids))
    n_ref_genomes_total = len(r_genome_ids) + len(r_genomes.intersection(user_genome_ids))
    if request.calcMode is SkaniCalculationMode.QVR:
        if n_query_genomes_total == 0 or n_ref_genomes_total == 0:
            raise HttpBadRequest(
                'No comparisons could be made as either all genomes in the query or reference list are not in the database. Uploaded genomes will need to be uploaded again.'
            )
    elif request.calcMode is SkaniCalculationMode.TRIANGLE:
        if n_query_genomes_total == 0:
            raise HttpBadRequest(
                'No comparisons could be made as all genomes in the query list are not in the database. Uploaded genomes will need to be uploaded again.'
            )
    else:
        raise HttpBadRequest(f'Unknown calculation mode.')

    # Create the parameter id, or retrieve it from the database
    param_id = get_or_set_db_param_id(db, request.version, request.params)

    # Set delete after only if it's a user upload job
    delete_after = None
    if len(user_genome_ids) > 0:
        if upload_metadata is not None:
            if upload_metadata.deleteAfter is not None:
                delete_after = upload_metadata.deleteAfter.name

    # Create the job with a unique name
    job = util_create_new_job(param_id, request, delete_after, db)

    # Upload the user genomes if they are provided
    d_file_name_to_genome_id = create_user_genomes(job.id, d_file_content, db)

    # Create the query / reference data for NCBI genomes
    [db.add(DbSkaniJobQuery(job_id=job.id, genome_id=x)) for x in q_genome_ids]
    [db.add(DbSkaniJobReference(job_id=job.id, genome_id=x)) for x in r_genome_ids]

    # Create the query / reference data for user genomes
    for user_file_name, user_genome_id in d_file_name_to_genome_id.items():
        if user_file_name in q_genomes:
            db.add(DbSkaniJobQuery(job_id=job.id, genome_id=user_genome_id))
        if user_file_name in r_genomes:
            db.add(DbSkaniJobReference(job_id=job.id, genome_id=user_genome_id))
    db.commit()

    # Set the job to ready status
    db.exec(sm.update(DbSkaniJob).where(DbSkaniJob.id == job.id).values(ready=True))
    db.commit()

    # Done
    return SkaniCreatedJobResponse(
        jobId=job.name
    )


def ani_validate_genomes(
        request: SkaniValidateGenomesRequest,
        db_gtdb: Session,
        db_ani: Session
) -> list[SkaniValidateGenomesResponse]:
    # Validate input arguments
    query_gids = set(request.genomes)
    if len(query_gids) > ANI_MAX_PAIRWISE:
        raise HttpBadRequest(f'You have exceeded the maximum number of genomes supported ({ANI_MAX_PAIRWISE:,}).')
    if len(query_gids) == 0:
        return list()

    # Convert the query genomes into canonical form
    d_canonical_to_gid = {canonical_gid(x): x for x in query_gids}

    # Retrieve the genomes from the GTDB database
    query_n_gids = (
        sm.select(
            DbGenomes.name,
            DbGenomes.formatted_source_id,
            DbMetadataTaxonomy.gtdb_domain,
            DbMetadataTaxonomy.gtdb_phylum,
            DbMetadataTaxonomy.gtdb_class,
            DbMetadataTaxonomy.gtdb_order,
            DbMetadataTaxonomy.gtdb_family,
            DbMetadataTaxonomy.gtdb_genus,
            DbMetadataTaxonomy.gtdb_species,
            DbMetadataTaxonomy.gtdb_representative
        )
        .join(DbMetadataTaxonomy, DbMetadataTaxonomy.id == DbGenomes.id)
        .join(DbMetadataNcbi, DbMetadataNcbi.id == DbGenomes.id)
        .where(DbGenomes.formatted_source_id.in_(set(d_canonical_to_gid.keys())))
        .where(DbMetadataNcbi.ncbi_genbank_assembly_accession != None)
        .where(DbMetadataTaxonomy.gtdb_domain != 'd__')
        .where(DbMetadataTaxonomy.gtdb_phylum != 'p__')
        .where(DbMetadataTaxonomy.gtdb_class != 'c__')
        .where(DbMetadataTaxonomy.gtdb_order != 'o__')
        .where(DbMetadataTaxonomy.gtdb_family != 'f__')
        .where(DbMetadataTaxonomy.gtdb_genus != 'g__')
        .where(DbMetadataTaxonomy.gtdb_species != 's__')
    )
    db_gtdb_rows = db_gtdb.exec(query_n_gids).all()

    # Stage the output
    d_out = dict()
    for row in db_gtdb_rows:

        # Revert to the format the user entered
        non_canonical_name = d_canonical_to_gid.get(row.formatted_source_id)
        if non_canonical_name is None:
            continue

        d_out[non_canonical_name] = SkaniValidateGenomesResponse(
            accession=non_canonical_name,
            isSpRep=row.gtdb_representative,
            gtdbDomain=row.gtdb_domain,
            gtdbPhylum=row.gtdb_phylum,
            gtdbClass=row.gtdb_class,
            gtdbOrder=row.gtdb_order,
            gtdbFamily=row.gtdb_family,
            gtdbGenus=row.gtdb_genus,
            gtdbSpecies=row.gtdb_species
        )

    # For any IDs that were not found, check the FastANI database
    missing_gids = query_gids - set(d_out.keys())
    if len(missing_gids) > 0:
        query_missing = sm.select(DbGenomesOnDisk.name, ).where(DbGenomesOnDisk.name.in_(missing_gids))
        db_ani_rows = db_ani.exec(query_missing).all()
        for genome_name in db_ani_rows:
            d_out[genome_name] = SkaniValidateGenomesResponse(
                accession=genome_name,
                isSpRep=None,
                gtdbDomain=None,
                gtdbPhylum=None,
                gtdbClass=None,
                gtdbOrder=None,
                gtdbFamily=None,
                gtdbGenus=None,
                gtdbSpecies=None
            )

    # Format the result
    out = list(sorted(d_out.values(), key=lambda x: x.accession))
    return out


def get_or_set_db_param_id(db: Session, version: SkaniVersion, params: SkaniParameters | None) -> int:
    # This is a routine defined in the skani schema
    query = sm.text(
        """
        SELECT *
        FROM skani.getOrSetParamId(
                CAST(:version AS VARCHAR),
                CAST(:min_af AS DOUBLE PRECISION),
                CAST(:both_min_af AS DOUBLE PRECISION),
                CAST(:preset AS VARCHAR),
                CAST(:c AS INTEGER),
                CAST(:faster_small AS BOOLEAN),
                CAST(:m AS INTEGER),
                CAST(:median AS BOOLEAN),
                CAST(:no_learned_ani AS BOOLEAN),
                CAST(:no_marker_index AS BOOLEAN),
                CAST(:robust AS BOOLEAN),
                CAST(:s AS DOUBLE PRECISION)
             );
        """
    )

    if params is None:
        parameters = {
            'version': version.name,
            'min_af': None,
            'both_min_af': None,
            'preset': None,
            'c': None,
            'faster_small': False,
            'm': None,
            'median': False,
            'no_learned_ani': False,
            'no_marker_index': False,
            'robust': False,
            's': None
        }
    else:
        parameters = {
            'version': version.name,
            'min_af': params.minAf,
            'both_min_af': params.bothMinAf,
            'preset': params.skaniPreset.name if params.skaniPreset else None,
            'c': params.cFactor,
            'faster_small': params.fasterSmall or False,
            'm': params.mFactor,
            'median': params.useMedian or False,
            'no_learned_ani': params.noLearnedAni or False,
            'no_marker_index': params.noMarkerIndex or False,
            'robust': params.robust or False,
            's': params.screen
        }
    result = db.exec(query, params=parameters).first()
    db.commit()

    if result is None or result[0] is None:
        raise HttpInternalServerError("Unable to retrieve or set the skani parameters.")
    return int(result[0])


def get_job_data_index_page(job_name: str, db_gtdb: Session, db_common: Session):
    query = (
        sm.select(
            DbSkaniJob.id,
            DbSkaniJob.mode,
            DbSkaniJob.completed,
            DbSkaniJob.error,
            DbSkaniParam.version,
            DbSkaniParam.min_af,
            DbSkaniParam.both_min_af,
            DbSkaniParam.preset,
            DbSkaniParam.c,
            DbSkaniParam.faster_small,
            DbSkaniParam.m,
            DbSkaniParam.median,
            DbSkaniParam.no_learned_ani,
            DbSkaniParam.no_marker_index,
            DbSkaniParam.robust,
            DbSkaniParam.s
        )
        .join(DbSkaniParam, DbSkaniParam.id == DbSkaniJob.param_id)
        .where(DbSkaniJob.name == job_name)
        .where(DbSkaniJob.deleted == False)
    )
    job_result = db_common.exec(query).first()
    if job_result is None:
        raise HttpNotFound(f'No job with this ID exists.')

    # Create the parameter output
    params = SkaniParameters(
        minAf=job_result.min_af,
        bothMinAf=job_result.both_min_af,
        skaniPreset=job_result.preset,
        cFactor=job_result.c,
        fasterSmall=job_result.faster_small,
        mFactor=job_result.m,
        useMedian=job_result.median,
        noLearnedAni=job_result.no_learned_ani,
        noMarkerIndex=job_result.no_marker_index,
        robust=job_result.robust,
        screen=job_result.s
    )

    # Load the genome lists
    d_genome_lists = util_get_job_query_reference_genomes(job_result.id, db_common)

    # Extract into a useful format
    ncbi_reference_genome_names = set()
    user_reference_genome_names = set()
    ncbi_query_genome_names = set()
    user_query_genome_names = set()
    for v in d_genome_lists:
        if v['origin'] == 'ncbi':
            if v['source'] == 'query':
                ncbi_query_genome_names.add(v['name'])
            elif v['source'] == 'reference':
                ncbi_reference_genome_names.add(v['name'])
        elif v['origin'] == 'user':
            if v['source'] == 'query':
                user_query_genome_names.add(v['name'])
            elif v['source'] == 'reference':
                user_reference_genome_names.add(v['name'])

    # For NCBI genomes, obtain the tax string if possible
    all_ncbi_ids = ncbi_reference_genome_names.union(ncbi_query_genome_names)
    d_canonical_to_gid = {canonical_gid(x): x for x in all_ncbi_ids}

    # Get the tax string
    query_tax = (
        sm.select(
            DbGenomes.name,
            DbGenomes.formatted_source_id,
            DbMetadataTaxonomy.gtdb_domain,
            DbMetadataTaxonomy.gtdb_phylum,
            DbMetadataTaxonomy.gtdb_class,
            DbMetadataTaxonomy.gtdb_order,
            DbMetadataTaxonomy.gtdb_family,
            DbMetadataTaxonomy.gtdb_genus,
            DbMetadataTaxonomy.gtdb_species,
            DbMetadataTaxonomy.gtdb_representative
        )
        .join(DbMetadataTaxonomy, DbMetadataTaxonomy.id == DbGenomes.id)
        .join(DbMetadataNcbi, DbMetadataNcbi.id == DbGenomes.id)
        .where(DbGenomes.formatted_source_id.in_(set(d_canonical_to_gid.keys())))
        .where(DbMetadataNcbi.ncbi_genbank_assembly_accession != None)
        .where(DbMetadataTaxonomy.gtdb_domain != 'd__')
        .where(DbMetadataTaxonomy.gtdb_phylum != 'p__')
        .where(DbMetadataTaxonomy.gtdb_class != 'c__')
        .where(DbMetadataTaxonomy.gtdb_order != 'o__')
        .where(DbMetadataTaxonomy.gtdb_family != 'f__')
        .where(DbMetadataTaxonomy.gtdb_genus != 'g__')
        .where(DbMetadataTaxonomy.gtdb_species != 's__')
    )
    db_gtdb_rows = db_gtdb.exec(query_tax).all()
    d_canonical_to_row = {x.formatted_source_id: x for x in db_gtdb_rows}

    # Map NCBI query records back to the query ids
    query = list()
    for q_gid in ncbi_query_genome_names:
        tax_row = d_canonical_to_row.get(canonical_gid(q_gid))
        if tax_row is None:
            query.append(
                SkaniValidateGenomesResponse(
                    accession=q_gid,
                    isUser=False
                )
            )
        else:
            query.append(
                SkaniValidateGenomesResponse(
                    accession=q_gid,
                    isUser=False,
                    isSpRep=tax_row.gtdb_representative,
                    gtdbDomain=tax_row.gtdb_domain,
                    gtdbPhylum=tax_row.gtdb_phylum,
                    gtdbClass=tax_row.gtdb_class,
                    gtdbOrder=tax_row.gtdb_order,
                    gtdbFamily=tax_row.gtdb_family,
                    gtdbGenus=tax_row.gtdb_genus,
                    gtdbSpecies=tax_row.gtdb_species
                )
            )

    # Add user genomes to the query list
    [query.append(SkaniValidateGenomesResponse(accession=x, isUser=True)) for x in user_query_genome_names]

    # Map NCBI reference records back to the query ids
    reference = list()
    for r_gid in ncbi_reference_genome_names:
        tax_row = d_canonical_to_row.get(canonical_gid(r_gid))
        if tax_row is None:
            reference.append(
                SkaniValidateGenomesResponse(
                    accession=r_gid,
                    isUser=False
                )
            )
        else:
            reference.append(
                SkaniValidateGenomesResponse(
                    accession=r_gid,
                    isUser=False,
                    isSpRep=tax_row.gtdb_representative,
                    gtdbDomain=tax_row.gtdb_domain,
                    gtdbPhylum=tax_row.gtdb_phylum,
                    gtdbClass=tax_row.gtdb_class,
                    gtdbOrder=tax_row.gtdb_order,
                    gtdbFamily=tax_row.gtdb_family,
                    gtdbGenus=tax_row.gtdb_genus,
                    gtdbSpecies=tax_row.gtdb_species
                )
            )

    # Add user genomes to the query list
    [reference.append(SkaniValidateGenomesResponse(accession=x, isUser=True)) for x in user_reference_genome_names]

    return SkaniJobDataIndexResponse(
        jobId=job_name,
        params=params,
        mode=job_result.mode,
        version=job_result.version,
        query=query,
        reference=reference
    )


def get_job_data_table_page(
        job_id_str: str,
        get_nulls: bool,
        get_self: bool,
        db_common: Session
) -> SkaniJobDataTableResponse:
    query = (
        sm.select(
            DbSkaniJob.id,
            DbSkaniJob.created,
            DbSkaniJob.param_id,
            DbSkaniJob.completed,
            DbSkaniJob.error,
            DbSkaniJob.mode,
        )
        .where(DbSkaniJob.name == job_id_str)
        .where(DbSkaniJob.deleted == False)
    )
    result = db_common.exec(query).first()
    if result is None:
        raise HttpNotFound(f'No job with this ID exists.')

    # If the job is not complete or in an error state, do not return any results
    if result.completed is None:
        return SkaniJobDataTableResponse(
            jobId=job_id_str,
            completed=False,
            error=result.error,
            rows=list()
        )
    if result.error is True:
        return SkaniJobDataTableResponse(
            jobId=job_id_str,
            completed=True,
            error=result.error,
            rows=list()
        )

    # Otherwise, get the genome ids and names
    qvr_list = util_get_job_query_reference_genomes(result.id, db_common)
    if len(qvr_list) == 0:
        raise HttpInternalServerError('The job has no genomes assigned to it. Please report this issue.')

    # Extract the genome ids
    query_genome_ids, reference_genome_ids = set(), set()
    d_genome_id_to_name = dict()
    for info in qvr_list:
        d_genome_id_to_name[info['id']] = info['name']
        if info['source'] == 'query':
            query_genome_ids.add(info['id'])
        elif info['source'] == 'reference':
            reference_genome_ids.add(info['id'])
    query_genome_ids, reference_genome_ids = list(query_genome_ids), list(reference_genome_ids)

    # Get the results from the database
    job_results = util_get_job_results(
        result.id, query_genome_ids, reference_genome_ids, result.mode, db_common
    )

    # Iterate over each pair
    out_rows = list()
    for qry_idx, qry_gid in enumerate(job_results.qry_ids):
        qry_name = d_genome_id_to_name[qry_gid]
        for ref_idx, ref_gid in enumerate(job_results.ref_ids):
            ref_name = d_genome_id_to_name[ref_gid]

            # Skip self matches if the user doesn't want them
            if not get_self and qry_gid == ref_gid:
                continue

            # Collect the values
            cur_ani = round(float(job_results.ani[qry_idx, ref_idx]), 2)
            cur_af_ref = round(float(job_results.af_ref[qry_idx, ref_idx]), 2)
            cur_af_qry = round(float(job_results.af_qry[qry_idx, ref_idx]), 2)

            # Skip if the user doesn't want distant values
            if cur_ani == 0 and cur_af_ref == 0 and cur_af_qry == 0 and not get_nulls:
                continue

            # Otherwise, save the row
            out_rows.append(
                SkaniResultTableRow(
                    qry=qry_name,
                    ref=ref_name,
                    ani=cur_ani,
                    afRef=cur_af_ref,
                    afQry=cur_af_qry,
                )
            )

    # Return the payload
    return SkaniJobDataTableResponse(
        jobId=job_id_str,
        completed=True,
        error=result.error,
        rows=out_rows
    )


def get_job_id_status(job_id_str: str, db_common: Session) -> SkaniJobStatusResponse:
    query = (
        sm.select(
            DbSkaniJob.id,
            DbSkaniJob.created,
            DbSkaniJob.completed,
            DbSkaniJob.error,
            DbSkaniJob.delete_after,
            DbSkaniJob.stdout,
            DbSkaniJob.stderr
        )
        .where(DbSkaniJob.name == job_id_str)
        .where(DbSkaniJob.deleted == False)
    )
    result = db_common.exec(query).first()
    if result is None:
        raise HttpNotFound(f'No job with this ID exists.')

    # If the job hasn't completed, get the queue position
    pos_in_queue, pending_jobs = None, None
    if result.completed is None:
        subquery = (
            sm.select(
                DbSkaniJob.id,
                sm.func.row_number().over(order_by=DbSkaniJob.created).label('position'),
                sm.func.count().over().label('total')
            )
            .where(DbSkaniJob.completed == None)
            .where(DbSkaniJob.deleted == False)
            .where(DbSkaniJob.ready == True)
            .subquery('queued')
        )
        stmt = sm.select(subquery.c.id, subquery.c.position, subquery.c.total).where(subquery.c.id == result.id)
        row = db_common.exec(stmt).first()

        pos_in_queue = row.position
        pending_jobs = row.total

    return SkaniJobStatusResponse(
        jobId=job_id_str,
        createdEpoch=int(result.created.timestamp()),
        completedEpoch=int(result.completed.timestamp()) if result.completed is not None else None,
        error=result.error,
        positionInQueue=pos_in_queue,
        totalPendingJobs=pending_jobs,
        stdout=result.stdout,
        stderr=result.stderr,
        deleteAfter=result.delete_after,
    )


# Utility methods
def get_genome_ids_from_ncbi_names(names: Collection[str], db: Session) -> dict[str, int]:
    """Given a list of NCBI genome names, return a mapping of name to genome ID."""
    if len(names) == 0:
        return dict()

    # Insert missing genomes into skani.genome
    insert_stmt = (
        sm.insert(DbSkaniGenome)
        .from_select(
            names=[DbSkaniGenome.ncbi_id],
            select=sm.select(DbGenomesOnDisk.id)
            .select_from(DbGenomesOnDisk)
            .outerjoin(DbSkaniGenome, DbSkaniGenome.ncbi_id == DbGenomesOnDisk.id)
            .where(DbGenomesOnDisk.name.in_(names))
            .where(DbSkaniGenome.ncbi_id == None)
        )
    )
    try:
        db.exec(insert_stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HttpInternalServerError('There was an error mapping NCBI ids, please report this issue.')

    # Query mapping from name to genome ID
    return_stmt = (
        sm.select(
            DbSkaniGenome.id,
            DbGenomesOnDisk.name,
        )
        .select_from(DbSkaniGenome)
        .join(DbGenomesOnDisk, DbGenomesOnDisk.id == DbSkaniGenome.ncbi_id)
        .where(DbGenomesOnDisk.name.in_(names))
    )
    results = db.exec(return_stmt).all()
    return {row.name: row.id for row in results}


def create_user_genomes(job_id: int, d_file_content: dict[str, tuple[str, str]], db: Session) -> dict[str, int]:
    if len(d_file_content) == 0:
        return dict()

    # Create the rows in the user_genome table
    rows = list()
    for cur_file_name, cur_file_content in d_file_content.items():
        rows.append(
            DbSkaniUserGenome(
                job_id=job_id,
                file_name=cur_file_name,
                fna=cur_file_content,
            )
        )
    [db.add(x) for x in rows]
    db.commit()

    user_ids = [x.id for x in rows]

    # Create a genome record for those genomes
    insert_stmt = (
        sm.insert(DbSkaniGenome)
        .from_select(
            names=[DbSkaniGenome.user_id],
            select=sm.select(DbSkaniUserGenome.id)
            .select_from(DbSkaniUserGenome)
            .outerjoin(DbSkaniGenome, DbSkaniGenome.user_id == DbSkaniUserGenome.id)
            .where(DbSkaniUserGenome.id.in_(user_ids))
            .where(DbSkaniGenome.user_id == None)
        )
    )
    db.exec(insert_stmt)
    db.commit()

    # Query mapping to genome ID
    return_stmt = (
        sm.select(
            DbSkaniGenome.id,
            DbSkaniUserGenome.file_name,
        )
        .select_from(DbSkaniGenome)
        .join(DbSkaniUserGenome, DbSkaniUserGenome.id == DbSkaniGenome.user_id)
        .where(DbSkaniUserGenome.id.in_(user_ids))
    )
    results = db.exec(return_stmt).all()
    return {row.file_name: row.id for row in results}


def util_create_new_job(param_id: int, request, delete_after, db: Session, retries: int = 3) -> DbSkaniJob:
    # Create the job record (with retries in case of job id collision)
    for _ in range(retries):

        # Create a new job id
        new_job_id = generate_random_job_name()

        try:
            # Create the job record
            job = DbSkaniJob(
                name=new_job_id,
                param_id=param_id,
                email=request.email,
                delete_after=delete_after,
                mode=request.calcMode.name,
                ready=False
            )
            db.add(job)
            db.commit()
            return job

        # Unlikely, but try again if this happens
        except IntegrityError:
            db.rollback()
            continue

        # Unrecoverable error, stop
        except Exception as e:
            print(e)
            raise HttpInternalServerError('There was an error creating the job. Please report this issue.')

    # Check to see if we actually got a job id
    raise HttpInternalServerError('There was an error creating the job. Please report this issue.')


def util_get_job_query_reference_genomes(job_id: int, db: Session):
    query = sm.text(
        """
        select g.id    AS genome_id,
               CASE
                   WHEN g.ncbi_id IS NOT NULL THEN god.name
                   WHEN g.user_id IS NOT NULL THEN ug.file_name
                   END as genome_name,
               CASE
                   WHEN g.ncbi_id IS NOT NULL THEN 'ncbi'
                   WHEN g.user_id IS NOT NULL THEN 'user'
                   END as origin,
               'query' AS source
        from skani.genome g
                 inner join skani.job_query jq ON jq.genome_id = g.id
                 left join skani.user_genome ug ON ug.id = g.user_id
                 left join genomes_on_disk god ON god.id = g.ncbi_id
        where jq.job_id = :job_id

        UNION

        select g.id        AS genome_id,
               CASE
                   WHEN g.ncbi_id IS NOT NULL THEN god.name
                   WHEN g.user_id IS NOT NULL THEN ug.file_name
                   END     as genome_name,
               CASE
                   WHEN g.ncbi_id IS NOT NULL THEN 'ncbi'
                   WHEN g.user_id IS NOT NULL THEN 'user'
                   END     as origin,
               'reference' AS source
        from skani.genome g
                 inner join skani.job_reference jr ON jr.genome_id = g.id
                 left join skani.user_genome ug ON ug.id = g.user_id
                 left join genomes_on_disk god ON god.id = g.ncbi_id
        where jr.job_id = :job_id;
        """
    )
    results = db.exec(query, params={'job_id': job_id}).all()
    out = list()
    for row in results:
        out.append(
            {
                'id': row.genome_id,
                'name': row.genome_name,
                'origin': row.origin,
                'source': row.source
            }
        )
    return out


def util_get_job_results(
        job_id: int,
        qry_ids: list[int],
        ref_ids: list[int],
        mode: SkaniCalculationMode,
        db: Session
) -> UtilSkaniJobResults:
    """
    Get the result rows for the given query and reference genome IDs.
    - ANI and AF values are saved as smallints and need to be divided by 100 to get the real value.
    - The query -> reference values are stored in a flat array, so need to be reshaped.
    - The reference -> query values are not stored, but can be extracted (i.e. not symmetric!)
    """
    query = (
        sm.select(
            DbSkaniJobResult.ani,
            DbSkaniJobResult.af_qry,
            DbSkaniJobResult.af_ref,
        )
        .where(DbSkaniJobResult.job_id == job_id)
    )
    result_row = db.exec(query).first()

    # Transform the ids into the rows and columns
    qry_gids_sorted = sorted(qry_ids)
    ref_gids_sorted = sorted(ref_ids)
    if mode is SkaniCalculationMode.TRIANGLE:
        ref_gids_sorted = qry_gids_sorted

    shape = (len(qry_gids_sorted), len(ref_gids_sorted))
    arr_ani = np.array(result_row.ani).reshape(shape) / 100
    arr_af_qry = np.array(result_row.af_qry).reshape(shape) / 100
    arr_af_ref = np.array(result_row.af_ref).reshape(shape) / 100

    return UtilSkaniJobResults(
        qry_ids=qry_gids_sorted,
        ref_ids=ref_gids_sorted,
        ani=arr_ani,
        af_qry=arr_af_qry,
        af_ref=arr_af_ref
    )


def skani_get_heatmap(
        job_name: str,
        cluster_by: str,
        db_gtdb: Session,
        db_common: Session
) -> SkaniJobDataHeatmapResponse:
    # method = af or ani
    query = (
        sm.select(
            DbSkaniJob.id,
            DbSkaniJob.created,
            DbSkaniJob.param_id,
            DbSkaniJob.completed,
            DbSkaniJob.error,
            DbSkaniJob.mode,
        )
        .where(DbSkaniJob.name == job_name)
        .where(DbSkaniJob.deleted == False)
    )
    job = db_common.exec(query).first()
    if job is None:
        raise HttpNotFound(f'No job with this ID exists.')

    # Exit early if the job isn't completed
    if job.completed is None:
        return SkaniJobDataHeatmapResponse(
            jobId=job_name,
            completed=False,
            error=False,
            ani=list(),
            af=list(),
            xLabels=list(),
            yLabels=list(),
            xSpecies=list(),
            ySpecies=list(),
            method='ani',
            spReps=list()
        )

    if job.error is True:
        return SkaniJobDataHeatmapResponse(
            jobId=job_name,
            completed=False,
            error=True,
            ani=list(),
            af=list(),
            xLabels=list(),
            yLabels=list(),
            xSpecies=list(),
            ySpecies=list(),
            method='ani',
            spReps=list()
        )

    # Get the genomes for this job
    genome_list = util_get_job_query_reference_genomes(job.id, db_common)
    query_list, reference_list = list(), list()
    genome_id_to_name = dict()
    for g in genome_list:
        if g['source'] == 'query':
            query_list.append(g['id'])
        elif g['source'] == 'reference':
            reference_list.append(g['id'])
        genome_id_to_name[g['id']] = g['name']

    # Get the taxonomy of any genomes that may be within the GTDB
    canonical_ncbi_names = {canonical_gid(x['name']) for x in genome_list if x['origin'] == 'ncbi'}
    d_canonical_name_to_taxinfo = get_taxonomy_for_canonical_genome_names(canonical_ncbi_names, db_gtdb)
    d_name_to_taxinfo = {x['name']: d_canonical_name_to_taxinfo[canonical_gid(x['name'])] for x in genome_list if
                         x['origin'] == 'ncbi'}

    # Create the genome id to species mapping and the species representative set
    gid_to_species = dict()
    gid_is_sp_rep = set()
    for cur_gid, spinfo in d_name_to_taxinfo.items():
        gid_to_species[cur_gid] = spinfo['species']
        if spinfo['is_rep']:
            gid_is_sp_rep.add(cur_gid)

    # Get the results for this job
    job_results = util_get_job_results(
        job.id, qry_ids=query_list, ref_ids=reference_list, mode=job.mode, db=db_common
    )

    # Map the genome ids to the index in the original matrix
    d_gid_to_ref_index = {x: idx for idx, x in enumerate(job_results.ref_ids)}
    d_gid_to_qry_index = {x: idx for idx, x in enumerate(job_results.qry_ids)}

    # Restructure the matrix into a symmetrical matrix
    shape = (len(job_results.qry_ids), len(job_results.ref_ids))
    arr_ani = np.zeros(shape=shape, dtype=float)
    arr_af = np.zeros(shape=shape, dtype=float)

    # Iterate over each pair
    for qry_idx, qry_gid in enumerate(job_results.qry_ids):
        for ref_idx, ref_gid in enumerate(job_results.ref_ids):

            # A non-symmetric matrix means we need to use the max AF
            is_symmetric = qry_gid in d_gid_to_ref_index and ref_gid in d_gid_to_qry_index

            # Collect the values
            ani = job_results.ani[qry_idx, ref_idx]
            af_qry = job_results.af_qry[qry_idx, ref_idx]
            af_ref = job_results.af_ref[qry_idx, ref_idx]

            # Store the values
            arr_ani[qry_idx, ref_idx] = ani

            # Store the values
            if is_symmetric:
                arr_af[qry_idx, ref_idx] = af_qry

                # Load the reverse
                ref_idx_rev = d_gid_to_ref_index[qry_gid]
                qry_idx_rev = d_gid_to_qry_index[ref_gid]
                arr_ani[qry_idx_rev, ref_idx_rev] = ani
                arr_af[qry_idx_rev, ref_idx_rev] = af_ref
            else:
                arr_af[qry_idx, ref_idx] = max(af_qry, af_ref)

    # Cluster the matrix depending on the clustering method
    try:
        if cluster_by == 'af':
            matrix, dendro_x, dendro_y = cluster_matrix(arr_af)
        else:
            matrix, dendro_x, dendro_y = cluster_matrix(arr_ani)

        # Create the output and re-order according to the clustering
        x_labels, y_labels = list(), list()
        x_gids, y_gids = list(), list()
        for x in dendro_x['leaves']:
            x_gids.append(job_results.ref_ids[x])
            x_labels.append(genome_id_to_name[job_results.ref_ids[x]])
        for y in dendro_y['leaves']:
            y_gids.append(job_results.qry_ids[y])
            y_labels.append(genome_id_to_name[job_results.qry_ids[y]])
        x_species = [gid_to_species.get(x, 'n/a') for x in x_labels]
        y_species = [gid_to_species.get(x, 'n/a') for x in y_labels]

        # Re-format the clustered matrix into the output
        out_ani, out_af = list(), list()
        for y_idx, (y_label, y_gid) in enumerate(zip(y_labels, y_gids)):
            qry_idx_original = d_gid_to_qry_index[y_gid]
            cur_ani_row, cur_af_row = list(), list()
            for x_idx, (x_label, x_gid) in enumerate(zip(x_labels, x_gids)):
                ref_idx_original = d_gid_to_ref_index[x_gid]
                if cluster_by == 'af':
                    ani = round(float(arr_ani[qry_idx_original, ref_idx_original]), 2)  # remove np floating decimals
                    af = round(float(matrix[y_idx, x_idx]), 2)
                else:
                    ani = round(float(matrix[y_idx, x_idx]), 2)
                    af = round(float(arr_af[qry_idx_original, ref_idx_original]), 2)
                cur_ani_row.append(ani)
                cur_af_row.append(af)
            out_ani.append(cur_ani_row)
            out_af.append(cur_af_row)

    except ValueError:
        # This can happen if there are empty values in the matrix
        print('sparse matrix')

        x_labels, y_labels = list(), list()
        x_species, y_species = list(), list()
        for qry_idx, qry_id in enumerate(job_results.qry_ids):
            qry_name = genome_id_to_name[qry_id]
            y_labels.append(qry_name)
            y_species.append(gid_to_species.get(qry_name, 'n/a'))
        for ref_idx, ref_id in enumerate(job_results.ref_ids):
            ref_name = genome_id_to_name[ref_id]
            x_labels.append(ref_name)
            x_species.append(gid_to_species.get(ref_name, 'n/a'))

        out_ani, out_af = list(), list()
        for y_idx in range(len(job_results.qry_ids)):
            out_ani.append([round(float(x), 2) for x in arr_ani[y_idx, :]])
            out_af.append([round(float(x), 2) for x in arr_af[y_idx, :]])

    return SkaniJobDataHeatmapResponse(
        jobId=job_name,
        completed=job.completed is not None,
        ani=out_ani,
        af=out_af,
        xLabels=x_labels,
        yLabels=y_labels,
        xSpecies=x_species,
        ySpecies=y_species,
        spReps=sorted(gid_is_sp_rep),
        method=cluster_by
    )


def get_taxonomy_for_canonical_genome_names(names: Collection[str], db_gtdb: Session) -> dict[str, str]:
    if not names:
        return dict()

    query = (
        sm.select(
            DbGenomes.formatted_source_id,
            DbMetadataTaxonomy.gtdb_domain,
            DbMetadataTaxonomy.gtdb_phylum,
            DbMetadataTaxonomy.gtdb_class,
            DbMetadataTaxonomy.gtdb_order,
            DbMetadataTaxonomy.gtdb_family,
            DbMetadataTaxonomy.gtdb_genus,
            DbMetadataTaxonomy.gtdb_species,
            DbMetadataTaxonomy.gtdb_representative
        )
        .select_from(DbGenomes)
        .join(DbMetadataTaxonomy, DbMetadataTaxonomy.id == DbGenomes.id)
        .where(DbGenomes.formatted_source_id.in_(names))
    )
    results = db_gtdb.exec(query).all()

    out = dict()
    for result in results:
        out[result.formatted_source_id] = {
            'species': result.gtdb_species,
            'is_rep': result.gtdb_representative
        }
    return out
