import random
from typing import List

import sqlalchemy as sa
import sqlmodel as sm
from fastapi import UploadFile
from sqlalchemy import sql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from api.config import ANI_MAX_PAIRWISE, ANI_USER_MAX_FILE_NAME_LENGTH, ANI_USER_MAX_FILE_COUNT, \
    ANI_USER_MAX_FILE_SIZE_MB_EACH, ANI_QUEUE_MAX_PENDING_JOBS
from api.db.common import DbGenomesOnDisk
from api.exceptions import HttpBadRequest, HttpInternalServerError, HttpNotFound
from api.model.ani import AniProgram, AniGenomeValidationResponse, AniGenomeValidationRequest, \
    AniJobRequest, AniParametersFastAni, AniParametersSkani, \
    AniJobResultResponseIndex, AniJobRequestDbModel, AniCreateJobResponse, \
    AniJobRequestDbModelUserFile
from api.util.cache import md5_string
from api.util.collection import deduplicate
from api.util.io import read_upload_file_bytes_limit


def ani_validate_genomes(request: AniGenomeValidationRequest, db_gtdb: Session, db_ani: Session) -> List[
    AniGenomeValidationResponse]:
    # Perform some validation on the input argumens
    query_gids = set(request.genomes)
    if len(query_gids) > ANI_MAX_PAIRWISE:
        raise HttpBadRequest(f'You have exceeded the maximum number of genomes supported ({ANI_MAX_PAIRWISE:,}).')
    if len(query_gids) == 0:
        return list()

    # Retrieve the genomes from the GTDB database
    query_n_gids = sa.select([
        Genome.name,
        MetadataTaxonomy.gtdb_domain,
        MetadataTaxonomy.gtdb_phylum,
        MetadataTaxonomy.gtdb_class,
        MetadataTaxonomy.gtdb_order,
        MetadataTaxonomy.gtdb_family,
        MetadataTaxonomy.gtdb_genus,
        MetadataTaxonomy.gtdb_species,
        MetadataTaxonomy.gtdb_representative
    ]). \
        select_from(sa.join(Genome, MetadataTaxonomy).join(MetadataNcbi)). \
        where(Genome.id == MetadataTaxonomy.id). \
        where(Genome.id == MetadataNcbi.id). \
        where(Genome.name.in_(list(query_gids))). \
        where(MetadataNcbi.ncbi_genbank_assembly_accession != None). \
        where(MetadataTaxonomy.gtdb_domain != 'd__'). \
        where(MetadataTaxonomy.gtdb_phylum != 'p__'). \
        where(MetadataTaxonomy.gtdb_class != 'c__'). \
        where(MetadataTaxonomy.gtdb_order != 'o__'). \
        where(MetadataTaxonomy.gtdb_family != 'f__'). \
        where(MetadataTaxonomy.gtdb_genus != 'g__'). \
        where(MetadataTaxonomy.gtdb_species != 's__')
    db_gtdb_rows = db_gtdb.execute(query_n_gids).fetchall()

    # Stage the output
    d_out = dict()
    for row in db_gtdb_rows:
        d_out[row.name] = AniGenomeValidationResponse(
            accession=row.name,
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
        query_missing = sa.select([CommonGenomesOnDisk.name]).where(CommonGenomesOnDisk.name.in_(list(missing_gids)))
        db_fastani_rows = db_ani.execute(query_missing).fetchall()
        for row in db_fastani_rows:
            d_out[row.name] = AniGenomeValidationResponse(
                accession=row.name,
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


def get_ani_job_queue_size(db: Session) -> int:
    """Get the current queue size of pending jobs in the ANI database."""
    query = (
        sm.select(sm.func.count())
        .select_from(DbAniJob)
        .where(DbAniJob.completed == None)
        .where(DbAniJob.error == None)
    )
    result = db.exec(query).first()
    return int(result)


async def ani_create_job(
        request: AniJobRequest,
        uploaded_files: List[UploadFile] | None,
        db: Session
) -> AniCreateJobResponse:
    """Enqueue an ANI job and return a unique ID to the user."""

    # TODO: Validate that only alphanumeric characters in the file name

    ani_user_max_file_size_bytes = ANI_USER_MAX_FILE_SIZE_MB_EACH * 1024 * 1024

    job_queue_size = get_ani_job_queue_size(db)
    if job_queue_size > ANI_QUEUE_MAX_PENDING_JOBS:
        raise HttpBadRequest(
            f'The job queue is full, please try again later. Contact us if this error persists for >24 hours.')

    # Perform validation on input arguments
    request.validate_email()
    request.validate_parameters()
    request.validate_genomes()

    # If user files have been uploaded, verify no restrictions are violated
    if uploaded_files is not None and len(uploaded_files) > 0:
        if len(uploaded_files) > ANI_USER_MAX_FILE_COUNT:
            raise HttpBadRequest(
                f'You have exceeded the maximum number of uploaded files ({ANI_USER_MAX_FILE_COUNT:,}).')
        for cur_file in uploaded_files:
            # Check the file name length limit
            if cur_file.filename is None:
                raise HttpBadRequest('One of the uploaded files is missing a filename.')
            else:
                if len(cur_file.filename) > ANI_USER_MAX_FILE_NAME_LENGTH:
                    raise HttpBadRequest(
                        f'{cur_file.filename}: name exceeds the limit of {ANI_USER_MAX_FILE_NAME_LENGTH:,} characters.')
            # Check the file size
            if cur_file.size is None:
                raise HttpBadRequest('One of the uploaded files is missing a size.')
            else:
                if cur_file.size > ani_user_max_file_size_bytes:
                    raise HttpBadRequest(
                        f'{cur_file.filename} exceeds the maximum file size of {ANI_USER_MAX_FILE_SIZE_MB_EACH:,} MB.')

    # After validation has completed, read the content of the files (not trusting file size metadata!)
    d_file_content = dict()
    if uploaded_files is not None and len(uploaded_files) > 0:
        for cur_file in uploaded_files:
            d_file_content[cur_file.filename] = await read_upload_file_bytes_limit(cur_file,
                                                                                   ani_user_max_file_size_bytes)

    # If user genomes have been supplied, then extract their names
    user_genome_ids = set(d_file_content.keys())

    # Deduplicate and preserve the order of the input genomes
    q_genomes, r_genomes = deduplicate(request.query), deduplicate(request.reference)
    all_ncbi_genomes = (set(q_genomes).union(set(r_genomes))) - user_genome_ids

    # Verify that the NCBI genomes exist on disk
    query = (
        sm.select(DbGenomesOnDisk.id, DbGenomesOnDisk.name)
        .where(DbGenomesOnDisk.name.in_(all_ncbi_genomes))
    )
    results = db.exec(query).all()
    genomes_in_db = {x.name: x.id for x in results}

    # Remove any NCBI query+reference genomes that aren't in the database
    q_genome_ids, r_genome_ids = list(), list()
    for x in q_genomes:
        if x not in user_genome_ids:
            q_genome_id = genomes_in_db.get(x)
            if q_genome_id is not None:
                q_genome_ids.append(q_genome_id)
    for x in r_genomes:
        if x not in user_genome_ids:
            r_genome_id = genomes_in_db.get(x)
            if r_genome_id is not None:
                r_genome_ids.append(r_genome_id)

    # Validate that there are still results after removing the accessions
    if len(q_genomes) == 0 or len(r_genomes) == 0:
        raise HttpBadRequest(
            'No comparisons could be made as either all genomes in the query or reference list are not in the database.')

    # Create the request payload
    db_model_user_files = list()
    delete_after = None
    if len(d_file_content) > 0:
        # Calculate the MD5 of each file
        for cur_file_name, cur_file_content in d_file_content.items():
            db_model_user_files.append(
                AniJobRequestDbModelUserFile(
                    name=cur_file_name,
                    md5=md5_string(cur_file_content),
                )
            )
        if request.userGenomes is not None and request.userGenomes.deleteAfter is not None:
            delete_after = request.userGenomes.deleteAfter

    # Important: To test uniqueness we must sort the genome lists
    db_request_json = AniJobRequestDbModel(
        query=sorted(q_genomes),
        reference=sorted(r_genomes),
        paramsFastAni=request.paramsFastAni,
        paramsSkani=request.paramsSkani,
        userGenomes=sorted(db_model_user_files, key=lambda x: x.name),
        program=request.program,
    ).model_dump_json()

    # Check if this job already exists
    query = sm.select(DbAniJob.id).where(DbAniJob.request == sm.cast(db_request_json, JSONB))
    existing_job = db.exec(query).first()
    if existing_job is not None:
        return AniCreateJobResponse(jobId=existing_job.strip())

    # Create the job record (with retries in case of job id collision)
    for _ in range(3):

        # Create a new job id (8 hex characters)
        new_job_id = random.randint(0, 2 ** 32 - 1)
        new_job_id = f'{new_job_id:08x}'

        try:
            # Add the base job row
            job_row = DbAniJob(id=new_job_id, email=request.email, request=db_request_json, delete_after=delete_after)
            db.add(job_row)

            # Add the user files if present
            if len(d_file_content) > 0:
                for cur_file_name, cur_file_content in d_file_content.items():
                    user_file_row = DbAniUserFna(
                        job_id=new_job_id,
                        name=cur_file_name,
                        data=cur_file_content
                    )
                    db.add(user_file_row)
            db.commit()

            # Return the payload
            return AniCreateJobResponse(jobId=new_job_id)

        except IntegrityError:
            db.rollback()
            continue

        except Exception as e:
            print(e)
            break

    raise HttpInternalServerError('Unable to create the job in the database, please report this.')


def get_job_genomes_and_metadata(job_id: int, table, db_common: Session, db_gtdb: Session) -> List[
    AniGenomeValidationResponse]:
    # Get the genome names from the ANI database
    sql_gids = (
        sa.select([
            CommonGenomesOnDisk.name,
        ])
        .select_from(sa.join(CommonGenomesOnDisk, table))
        .where(table.job_id == job_id)
        .where(table.genome_id == CommonGenomesOnDisk.id)
    )
    sql_gids_results = db_common.execute(sql_gids).fetchall()
    sql_gids_results = [x[0] for x in sql_gids_results]

    # Retrieve the genomes from the GTDB database
    query_n_gids = sa.select([
        Genome.name,
        MetadataTaxonomy.gtdb_domain,
        MetadataTaxonomy.gtdb_phylum,
        MetadataTaxonomy.gtdb_class,
        MetadataTaxonomy.gtdb_order,
        MetadataTaxonomy.gtdb_family,
        MetadataTaxonomy.gtdb_genus,
        MetadataTaxonomy.gtdb_species,
        MetadataTaxonomy.gtdb_representative
    ]). \
        select_from(sa.join(Genome, MetadataTaxonomy).join(MetadataNcbi)). \
        where(Genome.id == MetadataTaxonomy.id). \
        where(Genome.id == MetadataNcbi.id). \
        where(Genome.name.in_(list(sql_gids_results))). \
        where(MetadataNcbi.ncbi_genbank_assembly_accession != None). \
        where(MetadataTaxonomy.gtdb_domain != 'd__'). \
        where(MetadataTaxonomy.gtdb_phylum != 'p__'). \
        where(MetadataTaxonomy.gtdb_class != 'c__'). \
        where(MetadataTaxonomy.gtdb_order != 'o__'). \
        where(MetadataTaxonomy.gtdb_family != 'f__'). \
        where(MetadataTaxonomy.gtdb_genus != 'g__'). \
        where(MetadataTaxonomy.gtdb_species != 's__')
    db_gtdb_rows = db_gtdb.execute(query_n_gids).fetchall()

    # Stage the output
    tmp_out = dict()
    for row in db_gtdb_rows:
        tmp_out[row.name] = AniGenomeValidationResponse(
            accession=row.name,
            isSpRep=row.gtdb_representative,
            gtdbDomain=row.gtdb_domain,
            gtdbPhylum=row.gtdb_phylum,
            gtdbClass=row.gtdb_class,
            gtdbOrder=row.gtdb_order,
            gtdbFamily=row.gtdb_family,
            gtdbGenus=row.gtdb_genus,
            gtdbSpecies=row.gtdb_species
        )

    # Append rows that have no GTDB information
    out = list()
    for gid in sql_gids_results:
        if gid in tmp_out:
            out.append(tmp_out[gid])
        else:
            out.append(AniGenomeValidationResponse(
                accession=gid,
                isSpRep=None,
                gtdbDomain=None,
                gtdbPhylum=None,
                gtdbClass=None,
                gtdbOrder=None,
                gtdbFamily=None,
                gtdbGenus=None,
                gtdbSpecies=None
            ))
    return out


def get_ani_job_progress(
        job_id: str,
        db_common: Session,
        db_gtdb: Session
) -> AniJobResultResponseIndex:
    # Verify that the Job ID is a valid UUID
    try:
        job_id = int(job_id)
    except ValueError:
        raise HttpNotFound("No job exists with this id.")

    # Retrieve the job information from the database
    try:
        query = sa.select([
            CommonAniJob.request,
            CommonAniJob.result
        ]).where(CommonAniJob.id == job_id)
        results = db_common.execute(query).fetchall()
        if len(results) != 1:
            raise HttpNotFound("No job exists with this id.")
    except Exception as e:
        raise HttpInternalServerError("Unable to retrieve the job from the database, please report this.")

    # Otherwise, return the information for this job

    return

    # Retrieve job information from the common database
    qry_rows = get_job_genomes_and_metadata(job_id, CommonAniJobQuery, db_common, db_gtdb)
    ref_rows = get_job_genomes_and_metadata(job_id, CommonAniJobReference, db_common, db_gtdb)

    # Retrieve the job parameters
    sql_job_params = sql.text("""
        SELECT
            prog.name AS program_name,
            prog.version AS program_version,
            ps.min_af AS skani_min_af,
            ps.both_min_af AS skani_both_min_af,
            ps.preset AS skani_preset,
            ps.c AS skani_c,
            ps.faster_small AS skani_faster_small,
            ps.m AS skani_m,
            ps.median AS skani_median,
            ps.no_learned_ani AS skani_no_learned_ani,
            ps.no_marker_index AS skani_no_marker_index,
            ps.robust AS skani_robust,
            ps.s AS skani_s,
            pf.frag_len AS fastani_frag_len,
            pf.kmer_size AS fastani_kmer_size,
            pf.min_align_frac AS fastani_min_align_frac,
            pf.min_align_frag AS fastani_min_align_frag
        FROM ani.job j
        INNER JOIN ani.param p ON p.id = j.param_id
        LEFT JOIN ani.param_fastani pf ON pf.id = p.param_id_fastani
        LEFT JOIN ani.param_skani ps ON ps.id = p.param_id_skani
        INNER JOIN ani.program prog ON prog.id = ps.program_id OR prog.id = pf.program_id
        WHERE j.id = :job_id;
    """)
    results_job_params = db_common.execute(sql_job_params, {'job_id': job_id}).fetchall()
    if len(results_job_params) != 1:
        raise HttpInternalServerError(
            f'There was an error retrieving the job parameters from the database, please report this.')
    results_job_params = results_job_params[0]

    # Convert to the expected format
    program = AniProgram(name=results_job_params.program_name, version=results_job_params.program_version)

    params_fastani = None
    params_skani = None
    if program.is_fastani():
        params_fastani = AniParametersFastAni(**{
            'fastAniKmer': results_job_params.fastani_kmer_size,
            'fastAniFragLen': results_job_params.fastani_frag_len,
            'fastAniMinFrag': results_job_params.fastani_min_align_frag,
            'fastAniMinFrac': results_job_params.fastani_min_align_frac
        })

    elif program.is_skani():
        params_skani = AniParametersSkani(**{
            'skaniMinAf': results_job_params.skani_min_af,
            'skaniBothMinAf': results_job_params.skani_both_min_af,
            'skaniPreset': results_job_params.skani_preset,
            'skaniCFactor': results_job_params.skani_c,
            'skaniFasterSmall': results_job_params.skani_faster_small,
            'skaniMFactor': results_job_params.skani_m,
            'skaniUseMedian': results_job_params.skani_median,
            'skaniNoLearnedAni': results_job_params.skani_no_learned_ani,
            'skaniNoMarkerIndex': results_job_params.skani_no_marker_index,
            'skaniRobust': results_job_params.skani_robust,
            'skaniScreen': results_job_params.skani_s
        })

    else:
        raise HttpInternalServerError(f'The program name in the database is corrupted, please report this.')

    # Return the payload
    return AniJobResultResponseIndex(
        jobId=job_id,
        query=qry_rows,
        reference=ref_rows,
        paramsSkani=params_skani,
        paramsFastAni=params_fastani,
        program=program,
    )
