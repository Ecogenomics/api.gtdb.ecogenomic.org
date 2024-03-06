import os
import os
import subprocess
import tempfile
from collections import defaultdict
from functools import cmp_to_key
from typing import List, Set
from typing import Tuple, Optional, Union, Dict, Collection, Literal

import numpy as np
import sqlalchemy as sa
from redis import Redis
from rq import Queue, get_current_job
from rq.job import Job, JobStatus
from rq.queue import EnqueueData
from sqlalchemy import sql
from sqlalchemy.orm import Session

from api.config import FASTANI_MAX_PAIRWISE, \
    FASTANI_PRIORITY_SECRET, FASTANI_BIN, FASTANI_JOB_TIMEOUT, \
    FASTANI_JOB_RESULT_TTL, FASTANI_JOB_FAIL_TTL, FASTANI_JOB_RETRY, FASTANI_GENOME_DIR
from api.db.models import MetadataTaxonomy, Genome, GtdbFastaniGenome, GtdbFastaniResult, GtdbFastaniJob, MetadataNcbi, \
    GtdbFastaniParam, GtdbFastaniVersion, GtdbFastaniJobQuery, GtdbFastaniJobReference
from api.exceptions import HttpBadRequest, HttpNotFound, HttpInternalServerError
from api.model.fastani import FastAniJobResult, FastAniParameters, FastAniResult, FastAniJobRequest, FastAniConfig, \
    FastAniResultData, FastAniJobHeatmap, FastAniJobHeatmapData, FastAniHeatmapDataStatus, FastAniJobInfo, \
    FastAniJobStatus, FastAniGenomeValidationRequest, FastAniGenomeValidationResponse, FastAniJobMetadata
from api.util.collection import x_prod, deduplicate
from api.util.common import is_valid_email
from api.util.matrix import cluster_matrix
from api.util.ncbi import is_ncbi_accession


def get_fastani_config() -> FastAniConfig:
    return FastAniConfig(maxPairwise=FASTANI_MAX_PAIRWISE)


def get_job_query_gids(job_id: int, db: Session) -> List[str]:
    query = sql.text("""
        SELECT g.name
        FROM job_query jq
        INNER JOIN genome g ON g.id = jq.genome_id
        WHERE jq.job_id = :job_id
        ORDER BY g.name;
    """)
    result = db.execute(query, {'job_id': job_id}).fetchall()
    return [x.name for x in result]


def get_job_reference_gids(job_id, db: Session):
    query = sql.text("""
        SELECT g.name
        FROM job_reference jr
        INNER JOIN genome g ON g.id = jr.genome_id
        WHERE jr.job_id = :job_id
        ORDER BY g.name;
    """)
    result = db.execute(query, {'job_id': job_id}).fetchall()
    return [x.name for x in result]


def get_fastani_job_metadata(job_id: int, db: Session):
    query = sql.text("""
        select j.created, v.name, p.frag_len, p.kmer_size, p.min_align_frac, p.min_align_frag
        from job j
        INNER JOIN param p ON p.id = j.param_id
        INNER JOIN version v ON v.id = p.version
        WHERE j.id= :job_id;
    """)
    result = db.execute(query, {'job_id': job_id}).fetchone()
    if result is None:
        raise HttpNotFound("No such job.")
    dt_created = result.created
    params = FastAniParameters(
        version=result.name,
        frag_len=result.frag_len,
        kmer=result.kmer_size,
        min_frac=result.min_align_frac,
        min_frag=result.min_align_frag
    )

    return dt_created, params


def get_fastani_job_results(job_id: int, db: Session):
    query = sql.text("""
            SELECT
            gq.name AS q_name,
            gr.name AS r_name,
            r.ani,
            r.mapped_frag,
            r.total_frag,
            r.stdout,
            r.completed,
            r.error
        FROM job_result jr
                 INNER JOIN result r ON r.id = jr.result_id
                 INNER JOIN genome gq ON gq.id = r.qry_id
                 INNER JOIN genome gr ON gr.id = r.ref_id
        WHERE jr.job_id = :job_id
    """)
    results = db.execute(query, {'job_id': job_id}).fetchall()

    out = list()
    for row in results:

        # Check the state of the job
        if row.error:
            status = JobStatus.FAILED
        else:
            if row.completed:
                status = JobStatus.FINISHED
            else:
                status = JobStatus.QUEUED

        # Compute the AF
        if row.mapped_frag is not None and row.total_frag is not None:
            af = round(row.mapped_frag / row.total_frag, 4)
        else:
            af = None

        cur_data = FastAniResultData(
            ani=row.ani,
            af=af,
            mapped=row.mapped_frag,
            total=row.total_frag,
            status=status,
            stdout=row.stdout,
            stderr=None,
            cmd=None
        )
        out.append(FastAniResult(
            query=row.q_name,
            reference=row.r_name,
            data=cur_data
        ))

    return out


def get_fastani_job_progress(
        job_id: int,
        n_rows: Optional[int],
        page: Optional[int],
        sort_by: Optional[List[str]],
        sort_desc: Optional[List[bool]],
        db: Session
) -> FastAniJobResult:
    """Returns the progress of a FastANI job."""

    # Query the database for the query jobs
    query_gids = get_job_query_gids(job_id, db)
    reference_gids = get_job_reference_gids(job_id, db)
    dt_created, params = get_fastani_job_metadata(job_id, db)
    results = get_fastani_job_results(job_id, db)

    return FastAniJobResult(
        job_id=job_id,
        group_1=query_gids,
        group_2=reference_gids,
        parameters=params,
        results=results,
        positionInQueue=None
    )
    raise HttpInternalServerError('Unable to fetch job')


def fastani_job_to_rows(job_id: int, db: Session):
    """Retrieves a FastANI job from the database and converts it to rows."""
    job = get_fastani_job_progress(job_id, None, None, None, None, db)

    out = [
        ('job_id', job.job_id),
        ('group_1', ', '.join(job.group_1)),
        ('group_2', ', '.join(job.group_1)),
    ]

    # Parameters
    if job.parameters.version in {'1.0', '1.1', '1.2'}:
        skip = 'min_frac'
    else:
        skip = 'min_frag'
    out.extend([x for x in job.parameters if x[0] != skip])
    out.append([])

    # No results, exit.
    if len(job.results) == 0:
        out.append('No results.')
        return out

    # Header
    out.append(['query', 'reference', 'ani', 'af', 'mapped_fragments', 'total_fragments', 'status'])

    # Values
    for result in job.results:
        ani = 'n/a'
        af = 'n/a'
        mapped = 'n/a'
        total = 'n/a'

        if result.data.status is JobStatus.FINISHED:
            if result.data.ani is not None:
                ani = result.data.ani
                af = result.data.af
                mapped = result.data.mapped
                total = result.data.total
            else:
                ani = '< 80%'
                af = '-'
                mapped = '-'
                total = '-'

        out.append([
            result.query,
            result.reference,
            ani,
            af,
            mapped,
            total,
            result.data.status
        ])
    return out


def validate_genomes(group_a: List[str], group_b: List[str]):
    """Runs two collections of genomes to ensure they're valid."""
    n_pairwise = len(group_a) * len(group_b)
    if n_pairwise > FASTANI_MAX_PAIRWISE:
        raise HttpBadRequest(f'Too many pairwise comparisons: {n_pairwise:,} > '
                             f'{FASTANI_MAX_PAIRWISE:,}')
    if n_pairwise == 0:
        raise HttpBadRequest('No pairwise comparisons requested')

    # Validate each of the accessions
    invalid_accessions = set()
    for accession in group_a + group_b:
        if not is_ncbi_accession(accession):
            invalid_accessions.add(accession)
    if len(invalid_accessions) > 0:
        raise HttpBadRequest(f'One or more accessions are invalid: {invalid_accessions}')


def get_unique_job_ids(group_a: List[str], group_b: List[str],
                       params: FastAniParameters) -> Dict[str, Tuple[str, str]]:
    """Returns all unique job IDs for the comparisons that need to be performed."""
    out = dict()
    for gid_a, gid_b in x_prod(group_a, group_b, swap=True):
        out[get_unique_fastani_job_id(gid_a, gid_b, params)] = (gid_a, gid_b)
    return out


def get_existing_jobs(items: Collection[str], conn: Redis) -> Dict[str, Job]:
    """Returns a dictionary containing the Jobs if they exist."""
    out = dict()
    to_fetch = sorted(items)
    for job_id, job in zip(to_fetch, Job.fetch_many(to_fetch, conn)):
        if job is None:
            continue
        out[job_id] = job
    return out


def prepare_fastani_single_job(gid_a: str, gid_b: str, job_id: str, params: FastAniParameters) -> EnqueueData:
    """Enqueues a new FastANI job."""
    path_a = ncbi_accession_to_path(gid_a)
    path_b = ncbi_accession_to_path(gid_b)
    args = (path_a, path_b, params.kmer, params.frag_len, params.min_frag, params.min_frac, params.version)
    return Queue.prepare_data(run_fastani, job_id=job_id, meta={'q': gid_a, 'r': gid_b},
                              args=args, timeout=FASTANI_JOB_TIMEOUT, result_ttl=FASTANI_JOB_RESULT_TTL,
                              failure_ttl=FASTANI_JOB_FAIL_TTL, retry=FASTANI_JOB_RETRY)


def get_or_set_db_param_id(db: Session, params: FastAniParameters) -> int:
    query = sql.text(
        """
        SELECT * FROM getOrSetFastAniParamId(
            CAST(:version AS TEXT), 
            CAST(:frag_len AS INTEGER),
            CAST(:kmer AS SMALLINT),
            CAST(:min_frac AS DOUBLE PRECISION), 
            CAST(:min_frag AS INTEGER)
        );
        """
    )
    parameters = {
        'frag_len': params.frag_len,
        'kmer': params.kmer,
        'version': params.version,
        'min_frac': params.min_frac,
        'min_frag': params.min_frag
    }
    result = db.execute(query, parameters).fetchone()

    if result is None or len(result) == 0 or result[0] is None:
        raise HttpBadRequest("Unable to retrieve or set the FastANI parameters.")
    return int(result[0])


def associate_results_with_job(db: Session, email: Optional[str], param_id, result_ids, qry_genomes, ref_genomes):
    # Create the job id
    job_query = sa.insert(GtdbFastaniJob).values(email=email, param_id=param_id)
    job_id = db.execute(job_query).inserted_primary_key[0]
    db.commit()

    # Associate the query and reference genomes with this job id
    job_qry_rows_to_insert = [{'job_id': job_id, 'genome_id': x} for x in qry_genomes]
    job_qry_query = "INSERT INTO job_query (job_id, genome_id) VALUES (:job_id, :genome_id);"
    db.execute(job_qry_query, job_qry_rows_to_insert)
    db.commit()

    job_ref_rows_to_insert = [{'job_id': job_id, 'genome_id': x} for x in ref_genomes]
    job_ref_query = "INSERT INTO job_reference (job_id, genome_id) VALUES (:job_id, :genome_id);"
    db.execute(job_ref_query, job_ref_rows_to_insert)
    db.commit()

    # Associate the result ids with this job id
    job_result_rows_to_insert = [{'job_id': job_id, 'result_id': x} for x in result_ids]
    job_result_query = "INSERT INTO job_result (job_id, result_id) VALUES (:job_id, :result_id);"
    db.execute(job_result_query, job_result_rows_to_insert)
    db.commit()

    return job_id


def enqueue_fastani(request: FastAniJobRequest, db: Session) -> FastAniJobResult:
    """Enqueue FastANI jobs and return a unique ID to the user."""

    """
    Perform validation on input arguments
    """

    # Nullify either the alignment fraction/fragment based on the version
    if request.parameters.version in {'1.0', '1.1', '1.2'}:
        request.parameters.min_frac = None
    else:
        request.parameters.min_frag = None
    if request.parameters.min_frac is None and request.parameters.min_frag is None:
        raise HttpBadRequest('Either min_frac or min_frag must be provided.')

    # Validate e-mail address is valid if provided
    if request.email and len(request.email) > 3:
        if not is_valid_email(request.email):
            raise HttpBadRequest('Invalid e-mail address')
    else:
        request.email = None

    """
    Extract variables
    """

    is_priority = request.priority == FASTANI_PRIORITY_SECRET
    q_genomes, r_genomes = deduplicate(request.query), deduplicate(request.reference)

    # Error if too many pairwise comparisons, no comparisons, invalid NCBI accessions
    validate_genomes(q_genomes, r_genomes)

    # Subset the genomes to those that are in the database, and get the database ID
    all_genomes = set(q_genomes).union(set(r_genomes))
    query = sa.select([GtdbFastaniGenome.id, GtdbFastaniGenome.name]).where(GtdbFastaniGenome.name.in_(all_genomes))
    results = db.execute(query).fetchall()
    genomes_in_db = {x.name: x.id for x in results}
    q_genomes = [x for x in q_genomes if x in genomes_in_db]
    r_genomes = [x for x in r_genomes if x in genomes_in_db]

    qry_genomes = {x: genomes_in_db[x] for x in q_genomes if x in genomes_in_db}
    ref_genomes = {x: genomes_in_db[x] for x in r_genomes if x in genomes_in_db}
    qry_genomes_ids = frozenset(qry_genomes.values())
    ref_genomes_ids = frozenset(ref_genomes.values())

    # Validate that there are still results
    if len(qry_genomes) == 0 or len(r_genomes) == 0:
        raise HttpBadRequest('No comparisons could be made as one or more genomes were not found in the database.')

    # Create or retrieve the ID corresponding to the job parameters chosen
    param_id = get_or_set_db_param_id(db, request.parameters)

    # Create records for each of these jobs in the result table
    d_qry_ref_ids = get_result_ids_for_gid_params(param_id, qry_genomes_ids, ref_genomes_ids, db)
    result_ids = set(d_qry_ref_ids.values())

    # Create the job itself and associate the result ids with it
    job_id = associate_results_with_job(db, request.email, param_id, result_ids, qry_genomes_ids, ref_genomes_ids)

    # Return the payload
    return FastAniJobResult(job_id=job_id,
                            group_1=q_genomes,
                            group_2=r_genomes,
                            parameters=request.parameters,
                            results=[],
                            positionInQueue=None)


def get_fastani_results_from_job(job: Job, n_rows: Optional[int] = None, page: Optional[int] = None,
                                 sort_by: Optional[List[str]] = None,
                                 sort_desc: Optional[List[bool]] = None) -> List[FastAniResult]:
    """Given the main job id, return all results."""
    # Extract each of the results
    out = list()
    for dependency in job.fetch_dependencies():
        q = dependency.meta.get('q')
        r = dependency.meta.get('r')
        stdout = dependency.meta.get('stdout')
        stderr = dependency.meta.get('stderr')
        cmd = dependency.meta.get('cmd')
        ani, mapped, total = None, None, None
        dependency_result = dependency.return_value(refresh=False)
        if dependency_result is not None:
            ani, mapped, total = dependency_result
        if ani is not None and mapped is not None and total is not None:
            af = round(mapped / total, 4)
        else:
            af = None
        data = FastAniResultData(ani=ani, mapped=mapped, total=total,
                                 af=af,
                                 status=JobStatus[dependency.get_status(refresh=False).upper()],
                                 stdout=stdout, stderr=stderr, cmd=cmd)
        out.append(FastAniResult(query=q, reference=r, data=data))

    # Sort according to the sort parameters
    if sort_by and sort_desc and len(sort_by) == len(sort_desc):
        def sort_fn(a: FastAniResult, b: FastAniResult):
            a_ani = a.data.ani
            a_af = a.data.af
            a_mapped = a.data.mapped
            a_total = a.data.total
            a_status = a.data.status

            b_ani = b.data.ani
            b_af = b.data.af
            b_mapped = b.data.mapped
            b_total = b.data.total
            b_status = b.data.status

            for cur_sort_by, cur_sort_desc in zip(sort_by, sort_desc):
                cur_sort_desc_modifier = -1 if cur_sort_desc else 1
                if cur_sort_by == 'reference':
                    if a.reference > b.reference:
                        return 1 * cur_sort_desc_modifier
                    elif a.reference < b.reference:
                        return -1 * cur_sort_desc_modifier
                elif cur_sort_by == 'query':
                    if a.query > b.query:
                        return 1 * cur_sort_desc_modifier
                    elif a.query < b.query:
                        return -1 * cur_sort_desc_modifier
                elif cur_sort_by == 'ani':
                    if a_ani > b_ani:
                        return 1 * cur_sort_desc_modifier
                    elif a_ani < b_ani:
                        return -1 * cur_sort_desc_modifier
                elif cur_sort_by == 'af':
                    if a_af > b_af:
                        return 1 * cur_sort_desc_modifier
                    elif a_af < b_af:
                        return -1 * cur_sort_desc_modifier
                elif cur_sort_by == 'mapped':
                    if a_mapped > b_mapped:
                        return 1 * cur_sort_desc_modifier
                    elif a_mapped < b_mapped:
                        return -1 * cur_sort_desc_modifier
                elif cur_sort_by == 'total':
                    if a_total > b_total:
                        return 1 * cur_sort_desc_modifier
                    elif a_total < b_total:
                        return -1 * cur_sort_desc_modifier
                elif cur_sort_by == 'status':
                    if a_status > b_status:
                        return 1 * cur_sort_desc_modifier
                    elif a_status < b_status:
                        return -1 * cur_sort_desc_modifier
            return 0

        out.sort(key=cmp_to_key(sort_fn))

    # Idx to obtain
    if n_rows and page:
        idx_from = (page - 1) * n_rows
        idx_to = (page * n_rows)
        return out[idx_from:idx_to]
    return out


def ncbi_accession_to_path(accession: str, root_dir: str = FASTANI_GENOME_DIR) -> str:
    """Given an accession, return the path to the FASTA file."""
    return os.path.join(root_dir, accession[0:3], accession[4:7],
                        accession[7:10], accession[10:13], f'{accession}.fna.gz')


def run_fastani(
        q_path: str, r_path: str, kmer: int, frag_len: int, min_frag: int,
        min_frac: float, version: str
) -> Union[Tuple[Optional[float], int, int], Tuple[None, None, None]]:
    """Runs an individual instance of FastANI."""

    # Load the current rq job context to save the metadata to
    job = get_current_job()

    # Build arguments
    cmd = [FASTANI_BIN[version], '-r', r_path, '-q', q_path]
    if kmer is not None:
        cmd.extend(['-k', str(kmer)])
    if frag_len is not None:
        cmd.extend(['--fragLen', str(frag_len)])
    if version in {'1.0', '1.1', '1.2'}:
        if min_frag is not None:
            cmd.extend(['--minFrag', str(min_frag)])
    else:
        if min_frac is not None:
            cmd.extend(['--minFraction', str(min_frac)])

    # Run the program to a temporary directory
    with tempfile.TemporaryDirectory(prefix='fastani_') as tmpdir:
        output = os.path.join(tmpdir, 'output.txt')
        cmd.extend(['-o', output])

        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, encoding='utf-8')
        stdout, stderr = p.communicate()

        # Save output (as exceptions will return None)
        if job:
            job.meta['stderr'] = stderr
            job.meta['cmd'] = ' '.join(cmd)
            job.save_meta()

        # Verify that the program ran correctly
        if p.returncode != 0:
            raise Exception(f'FastANI failed with exit code: {p.returncode}')

        # Parse the output file
        with open(output) as f:
            lines = f.readlines()
            if len(lines) != 1:
                return None, None, None
            line = lines[0].strip().split()
            if len(line) != 5:
                raise Exception(f'Malformed output file: {lines}')
            return float(line[2]), int(line[3]), int(line[4])


def get_unique_fastani_job_id(gid_a: str, gid_b: str, params: FastAniParameters) -> str:
    """Generates a unique job id for FastANI jobs."""
    key = ['ANI', gid_a, gid_b, params.frag_len, params.kmer,
           params.min_frag, params.min_frac, params.version]
    return '|'.join(map(lambda x: str(x), key))


def can_use_previous_job(job: Optional[Job], refresh: bool = False) -> bool:
    """Determines this Job is still valid for processing."""
    if job is None:
        return False
    status = job.get_status(refresh=refresh)
    if status == JobStatus.CANCELED.value:
        return False
    if status == JobStatus.DEFERRED.value:
        return True
    if status == JobStatus.FAILED.value:
        return False
    if status == JobStatus.FINISHED.value:
        return True
    if status == JobStatus.QUEUED.value:
        return True
    if status == JobStatus.SCHEDULED.value:
        return True
    if status == JobStatus.STARTED.value:
        return True
    if status == JobStatus.STOPPED.value:
        return False
    return False


def _format_job_status(data: Optional[FastAniResultData]) -> FastAniHeatmapDataStatus:
    """Converts the RQ job status into one interpretable by the frontend."""
    if data.status in {JobStatus.FAILED, JobStatus.CANCELED, JobStatus.STOPPED}:
        return FastAniHeatmapDataStatus.ERROR
    if data.status in {JobStatus.SCHEDULED, JobStatus.QUEUED, JobStatus.STARTED, JobStatus.DEFERRED}:
        return FastAniHeatmapDataStatus.QUEUED
    if data.status in {JobStatus.FINISHED}:
        return FastAniHeatmapDataStatus.FINISHED
    return FastAniHeatmapDataStatus.ERROR


def fastani_heatmap(job_id: int, method: Literal['ani', 'af'], db_gtdb: Session, db_fastani: Session):
    # Retrieve the job information
    if job_id is None or job_id <= 0:
        return HttpNotFound('No such job.')
    jobs = get_fastani_job_progress(job_id, None, None, None, None, db=db_fastani)

    # Index the labels
    set_group_1 = frozenset(jobs.group_1)
    set_group_2 = frozenset(jobs.group_2)
    idx_to_label = sorted(set_group_1 | set_group_2)
    label_to_idx = {lab: i for i, lab in enumerate(idx_to_label)}

    # Get the species of the query and reference genomes
    query = sa.select([Genome.id_at_source,
                       MetadataTaxonomy.gtdb_species,
                       MetadataTaxonomy.gtdb_representative]). \
        select_from(sa.join(Genome, MetadataTaxonomy)). \
        where(Genome.id_at_source.in_(set_group_1 | set_group_2))
    gid_to_species = dict()
    gid_is_sp_rep = set()
    for row in db_gtdb.execute(query):
        gid_to_species[row.id_at_source] = row.gtdb_species
        if row.gtdb_representative:
            gid_is_sp_rep.add(row.id_at_source)

    # Index the data by label
    d_results = defaultdict(dict)
    for result in jobs.results:
        d_results[result.query][result.reference] = result.data

    # Create the output array
    arr = np.zeros((len(label_to_idx), len(label_to_idx)))
    d_status_cnt = defaultdict(lambda: 0)
    for result in jobs.results:
        qry_idx = label_to_idx[result.query]
        ref_idx = label_to_idx[result.reference]
        cur_status = _format_job_status(result.data)
        d_status_cnt[cur_status] += 1
        if cur_status is FastAniHeatmapDataStatus.ERROR:
            arr[qry_idx, ref_idx] = -1
        else:
            arr[qry_idx, ref_idx] = getattr(result.data, method) or 0
    pct_done = round(100 * (1 - d_status_cnt[FastAniHeatmapDataStatus.QUEUED] / len(jobs.results)), 2)

    # If there is only one observation then just return the value
    if arr.shape == (1, 1):
        matrix = arr
        dendro_x = {'leaves': [0]}
        dendro_y = {'leaves': [0]}
    else:
        # Cluster the values
        matrix, dendro_x, dendro_y = cluster_matrix(arr)

    # Create the output
    out = list()
    x_labels = [idx_to_label[x] for x in dendro_x['leaves']]
    y_labels = [idx_to_label[x] for x in dendro_y['leaves']]
    x_species = [gid_to_species.get(x, 'n/a') for x in x_labels]
    y_species = [gid_to_species.get(x, 'n/a') for x in y_labels]
    for x_idx, x_label in enumerate(x_labels):
        for y_idx, y_label in enumerate(y_labels):

            data: Optional[FastAniResultData] = d_results[x_label].get(y_label)
            if data is not None:
                if method == 'ani':
                    ani = matrix[y_idx, x_idx]
                    af = data.af if data.af is not None else 0
                else:
                    ani = data.ani if data.ani is not None else 0
                    af = matrix[y_idx, x_idx]

                out.append(FastAniJobHeatmapData(
                    x=x_idx,
                    y=y_idx,
                    ani=ani,
                    af=af,
                    mapped=data.mapped,
                    total=data.total,
                    status=_format_job_status(data)
                ))

    # Return the object
    return FastAniJobHeatmap(
        data=out,
        method=method,
        xLabels=x_labels,
        yLabels=y_labels,
        xSpecies=x_species,
        ySpecies=y_species,
        spReps=sorted(gid_is_sp_rep),
        pctDone=pct_done,
    )


def get_fastani_job_info(job_id: int, db: Session) -> FastAniJobInfo:
    query = sql.text("""
        SELECT j.created,
               agg.completed,
               agg.error,
               agg.count
        FROM job j
                 INNER JOIN (SELECT jr.job_id,
                                    r.completed,
                                    r.error,
                                    COUNT(*)
                             FROM job_result jr
                                      INNER JOIN result r ON r.id = jr.result_id
                             WHERE jr.job_id = :job_id
                             GROUP BY jr.job_id, r.completed, r.error) agg ON agg.job_id = j.id
        WHERE j.id = :job_id
    """)
    rows = db.execute(query, {'job_id': job_id}).fetchall()
    if rows is None or len(rows) == 0:
        raise HttpNotFound(f"No such job id: '{job_id}'")

    if len(rows) == 1:
        if rows[0].error:
            status = FastAniJobStatus.ERROR
        else:
            if rows[0].completed:
                status = FastAniJobStatus.FINISHED
            else:
                status = FastAniJobStatus.QUEUED
    else:
        status = FastAniJobStatus.RUNNING

    return FastAniJobInfo(
        jobId=job_id,
        createdOn=rows[0].created.timestamp(),
        status=status
    )

    # with Redis(host=REDIS_HOST, password=REDIS_PASS) as conn:
    #     try:
    #         job = Job.fetch(job_id, connection=conn)
    #
    #         # Check to see if the dependencies of the job are completed
    #         if job.is_deferred or job.is_started:
    #             status = FastAniJobStatus.RUNNING
    #
    #             all_finished = True
    #             for job_dependency in job.fetch_dependencies():
    #                 if job_dependency.is_failed:
    #                     status = FastAniJobStatus.ERROR
    #                     break
    #                 all_finished = all_finished and job_dependency.is_finished
    #
    #             if status is not FastAniJobStatus.ERROR:
    #                 if all_finished:
    #                     status = FastAniJobStatus.FINISHED
    #                 else:
    #                     status = FastAniJobStatus.RUNNING
    #         elif job.is_queued:
    #             status = FastAniJobStatus.QUEUED
    #         elif job.is_finished:
    #             status = FastAniJobStatus.FINISHED
    #         else:
    #             status = FastAniJobStatus.ERROR
    #
    #         return FastAniJobInfo(
    #             jobId=job_id,
    #             createdOn=job.created_at.timestamp(),
    #             status=status,
    #         )
    #     except NoSuchJobError:
    #         raise HttpNotFound(f"No such job id: '{job_id}'")
    # raise HttpInternalServerError('Unable to fetch job')


def get_result_ids_for_gid_params(param_id: int, qry_gids: Set[int], ref_gids: Set[int], db: Session) -> Dict[
    Tuple[int, int], int]:
    # Generate the unique pairwise comparisons
    unq_tuples = set()
    for q_gid in qry_gids:
        for r_gid in ref_gids:
            unq_tuples.add((q_gid, r_gid))
            unq_tuples.add((r_gid, q_gid))

    # Create the SQL query that will obtain all result ids matching the input
    or_groups = list()
    for cur_q, cur_r in unq_tuples:
        or_groups.append(sa.and_(GtdbFastaniResult.qry_id == cur_q, GtdbFastaniResult.ref_id == cur_r))
    query_all = sa.select([GtdbFastaniResult.id, GtdbFastaniResult.qry_id, GtdbFastaniResult.ref_id]).where(
        GtdbFastaniResult.param_id == param_id)
    query_all = query_all.where(sa.or_(*or_groups))

    # If there are rows to insert, proceed
    if len(unq_tuples) > 0:

        # Fetch the rows that already exist
        rows_existing = db.execute(query_all).fetchall()

        # Remove the existing rows from the set
        dedup_tuples = unq_tuples - {(x.qry_id, x.ref_id) for x in rows_existing}

        # Insert the remaining rows
        if len(dedup_tuples) > 0:
            rows_to_insert = [{'qry_id': x[0], 'ref_id': x[1], 'param_id': param_id} for x in dedup_tuples]
            query = "INSERT INTO result (qry_id, ref_id, param_id) VALUES (:qry_id, :ref_id, :param_id);"
            db.execute(query, rows_to_insert)
            db.commit()

    # Fetch the result ids for the query
    rows_out = db.execute(query_all).fetchall()

    # Subset those to the requested ids
    out = dict()
    for cur_result_id, cur_qry_id, cur_ref_id in rows_out:
        out[(cur_qry_id, cur_ref_id)] = cur_result_id

    return out


def fastani_validate_genomes(request: FastAniGenomeValidationRequest, db_gtdb: Session, db_fastani: Session) -> List[
    FastAniGenomeValidationResponse]:
    # Perform some validation on the input argumens
    query_gids = set(request.genomes)
    max_limit = 5_000
    if len(query_gids) > max_limit:
        raise HttpBadRequest(f'You have exceeded the maximum number of genomes supported ({max_limit:,}).')
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
        d_out[row.name] = FastAniGenomeValidationResponse(
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
        query_missing = sa.select([GtdbFastaniGenome.name]).where(GtdbFastaniGenome.name.in_(list(missing_gids)))
        db_fastani_rows = db_fastani.execute(query_missing).fetchall()
        for row in db_fastani_rows:
            d_out[row.name] = FastAniGenomeValidationResponse(
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


def get_fastani_job_metadata_control(job_id: int, db_gtdb: Session, db_fastani: Session) -> FastAniJobMetadata:
    # Retrieve the parameters
    params_qry = sa.select([
        GtdbFastaniParam.frag_len,
        GtdbFastaniParam.kmer_size,
        GtdbFastaniParam.min_align_frac,
        GtdbFastaniParam.min_align_frag, GtdbFastaniVersion.name
    ]).join(GtdbFastaniJob, GtdbFastaniJob.param_id == GtdbFastaniParam.id).join(GtdbFastaniVersion,
                                                                                 GtdbFastaniVersion.id == GtdbFastaniParam.version).where(
        GtdbFastaniJob.id == job_id)
    params_rows = db_fastani.execute(params_qry).fetchone()

    if params_rows is None:
        raise HttpNotFound(f'No job exists with the ID: {job_id}')

    params = FastAniParameters(
        version=params_rows.name,
        frag_len=params_rows.frag_len,
        kmer=params_rows.kmer_size,
        min_frac=params_rows.min_align_frac,
        min_frag=params_rows.min_align_frag
    )

    # Retrieve the genome accessions in the job
    gid_query_qry = sa.select([GtdbFastaniGenome.name]).join(GtdbFastaniJobQuery,
                                                             GtdbFastaniJobQuery.genome_id == GtdbFastaniGenome.id).where(
        GtdbFastaniJobQuery.job_id == job_id)
    gid_query_rows = db_fastani.execute(gid_query_qry).fetchall()
    d_query_gids = {x.name: FastAniGenomeValidationResponse(accession=x.name) for x in gid_query_rows}

    gid_ref_qry = sa.select([GtdbFastaniGenome.name]).join(GtdbFastaniJobReference,
                                                           GtdbFastaniJobReference.genome_id == GtdbFastaniGenome.id).where(
        GtdbFastaniJobReference.job_id == job_id)
    gid_ref_rows = db_fastani.execute(gid_ref_qry).fetchall()
    d_ref_gids = {x.name: FastAniGenomeValidationResponse(accession=x.name) for x in gid_ref_rows}

    # Retrieve the genome metadata
    all_gids = list(set(d_query_gids).union(d_ref_gids))
    metadata_qry = sa.select([
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
        where(Genome.name.in_(all_gids)). \
        where(MetadataNcbi.ncbi_genbank_assembly_accession != None). \
        where(MetadataTaxonomy.gtdb_domain != 'd__'). \
        where(MetadataTaxonomy.gtdb_phylum != 'p__'). \
        where(MetadataTaxonomy.gtdb_class != 'c__'). \
        where(MetadataTaxonomy.gtdb_order != 'o__'). \
        where(MetadataTaxonomy.gtdb_family != 'f__'). \
        where(MetadataTaxonomy.gtdb_genus != 'g__'). \
        where(MetadataTaxonomy.gtdb_species != 's__')
    metadata_rows = db_gtdb.execute(metadata_qry).fetchall()

    # Merge the rows
    for row in metadata_rows:
        gid = row.name
        if gid in d_query_gids:
            d_query_gids[gid] = FastAniGenomeValidationResponse(
                accession=gid,
                isSpRep=row.gtdb_representative,
                gtdbDomain=row.gtdb_domain,
                gtdbPhylum=row.gtdb_phylum,
                gtdbClass=row.gtdb_class,
                gtdbOrder=row.gtdb_order,
                gtdbFamily=row.gtdb_family,
                gtdbGenus=row.gtdb_genus,
                gtdbSpecies=row.gtdb_species
            )
        if gid in d_ref_gids:
            d_ref_gids[gid] = FastAniGenomeValidationResponse(
                accession=gid,
                isSpRep=row.gtdb_representative,
                gtdbDomain=row.gtdb_domain,
                gtdbPhylum=row.gtdb_phylum,
                gtdbClass=row.gtdb_class,
                gtdbOrder=row.gtdb_order,
                gtdbFamily=row.gtdb_family,
                gtdbGenus=row.gtdb_genus,
                gtdbSpecies=row.gtdb_species
            )
    out = FastAniJobMetadata(
        query=sorted(d_query_gids.values(), key=lambda x: x.accession),
        reference=sorted(d_ref_gids.values(), key=lambda x: x.accession),
        parameters=params
    )
    return out
