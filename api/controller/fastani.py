import os
import subprocess
import tempfile
from collections import defaultdict
from functools import cmp_to_key
from typing import List
from typing import Tuple, Optional, Union, Dict, Collection, Literal

import numpy as np
import sqlalchemy as sa
from redis import Redis
from rq import Queue, get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from rq.queue import EnqueueData
from sqlalchemy.orm import Session

from api.config import REDIS_HOST, REDIS_PASS, FASTANI_MAX_PAIRWISE, \
    FASTANI_Q_NORMAL, FASTANI_Q_PRIORITY, FASTANI_PRIORITY_SECRET, FASTANI_BIN, FASTANI_JOB_TIMEOUT, \
    FASTANI_JOB_RESULT_TTL, FASTANI_JOB_FAIL_TTL, FASTANI_JOB_RETRY, FASTANI_GENOME_DIR, FASTANI_Q_LOW, \
    FASTANI_MAX_PAIRWISE_LOW
from api.db.models import MetadataTaxonomy, Genome
from api.exceptions import HttpBadRequest, HttpNotFound, HttpInternalServerError
from api.model.fastani import FastAniJobResult, FastAniParameters, FastAniResult, FastAniJobRequest, FastAniConfig, \
    FastAniResultData, FastAniJobHeatmap, FastAniJobHeatmapData, FastAniHeatmapDataStatus
from api.util.collection import x_prod, deduplicate
from api.util.matrix import cluster_matrix
from api.util.ncbi import is_ncbi_accession


def get_fastani_config() -> FastAniConfig:
    return FastAniConfig(maxPairwise=FASTANI_MAX_PAIRWISE, maxPairwiseLow=FASTANI_MAX_PAIRWISE_LOW)


def get_fastani_job_progress(job_id: str, n_rows: Optional[int] = None, page: Optional[int] = None,
                             sort_by: Optional[List[str]] = None,
                             sort_desc: Optional[List[bool]] = None) -> FastAniJobResult:
    """Returns the progress of a FastANI job."""
    with Redis(host=REDIS_HOST, password=REDIS_PASS) as conn:
        try:
            job = Job.fetch(job_id, connection=conn)
            group_1, group_2 = job.meta.get('group_1'), job.meta.get('group_2')
            job_pos = job.get_position()
            job_position = None
            if job_pos:
                job_position = max(0, job_pos - len(group_1) * len(group_2) * 2)
            return FastAniJobResult(job_id=job_id,
                                    group_1=group_1,
                                    group_2=group_2,
                                    parameters=FastAniParameters.parse_raw(job.meta.get('parameters')),
                                    results=get_fastani_results_from_job(job, n_rows, page, sort_by, sort_desc),
                                    positionInQueue=job_position)
        except NoSuchJobError:
            raise HttpNotFound(f"No such job id: '{job_id}'")
    raise HttpInternalServerError('Unable to fetch job')


def fastani_job_to_rows(job_id: str):
    """Retrieves a FastANI job from the database and converts it to rows."""
    job = get_fastani_job_progress(job_id)

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
    # if n_pairwise > FASTANI_MAX_PAIRWISE:
    #     raise HttpBadRequest(f'Too many pairwise comparisons: {n_pairwise:,} > '
    #                          f'{FASTANI_MAX_PAIRWISE:,}')
    if n_pairwise == 0:
        raise HttpBadRequest('No pairwise comparisons requested')

    # Validate each of the accessions
    for accession in group_a + group_b:
        if not is_ncbi_accession(accession):
            raise HttpBadRequest('One or more accessions are invalid')


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


def enqueue_fastani(request: FastAniJobRequest) -> FastAniJobResult:
    """Enqueue FastANI jobs and return a unique ID to the user."""

    # Extract variables
    is_priority = request.priority == FASTANI_PRIORITY_SECRET
    q_genomes, r_genomes = deduplicate(request.query), deduplicate(request.reference)

    # Validation
    validate_genomes(q_genomes, r_genomes)

    # Generate all unique FastANI job ids
    unique_ids = get_unique_job_ids(q_genomes, r_genomes, request.parameters)

    # Set the target queue
    n_pairwise = len(q_genomes) * len(r_genomes)
    if n_pairwise > FASTANI_MAX_PAIRWISE_LOW:
        raise HttpBadRequest(f'Too many pairwise comparisons: {n_pairwise:,} > {FASTANI_MAX_PAIRWISE_LOW:,}')
    elif n_pairwise > FASTANI_MAX_PAIRWISE:
        target_queue = FASTANI_Q_LOW
    else:
        target_queue = FASTANI_Q_PRIORITY if is_priority else FASTANI_Q_NORMAL

    # Create the job
    with Redis(host=REDIS_HOST, password=REDIS_PASS) as conn:
        q = Queue(target_queue, connection=conn)

        # Check if any Jobs already exist
        existing_jobs = get_existing_jobs(unique_ids.keys(), conn)

        # Create each of the individual FastANI comparison jobs
        prev_jobs: List[Job] = list()
        to_enqueue: List[EnqueueData] = list()
        for job_id, (gid_a, gid_b) in unique_ids.items():

            # Was there an existing job with the same id?
            existing_job = existing_jobs.get(job_id)

            # The job does not exist, so we must create it
            if existing_job is None:
                to_enqueue.append(prepare_fastani_single_job(gid_a, gid_b, job_id, request.parameters))

            # The job exists, and can be re-used (running, or finished)
            elif can_use_previous_job(existing_job):
                prev_jobs.append(existing_job)

            # The job exists, but has failed, retry it
            else:
                prev_jobs.append(existing_job.requeue())

        # Bulk enqueue those which need to be created
        prev_jobs.extend(q.enqueue_many(to_enqueue))

        # Create the main job that will wait for all the individual jobs
        job = q.enqueue(print, args=(), depends_on=prev_jobs,
                        meta={'parameters': request.parameters.json(),
                              'group_1': q_genomes, 'group_2': r_genomes},
                        timeout=FASTANI_JOB_TIMEOUT,
                        result_ttl=FASTANI_JOB_RESULT_TTL,
                        failure_ttl=FASTANI_JOB_FAIL_TTL,
                        retry=FASTANI_JOB_RETRY)

        return FastAniJobResult(job_id=job.get_id(),
                                group_1=q_genomes,
                                group_2=r_genomes,
                                parameters=request.parameters,
                                results=[],
                                positionInQueue=q.get_job_position(job))


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


def run_fastani(q_path: str, r_path: str, kmer: int, frag_len: int, min_frag: int,
                min_frac: float, version: str) -> Union[Tuple[Optional[float], int, int],
Tuple[None, None, None]]:
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


def fastani_heatmap(job_id: str, method: Literal['ani', 'af'], db: Session):
    jobs = get_fastani_job_progress(job_id)

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
    for row in db.execute(query):
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
