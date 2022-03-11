import os
import subprocess
import tempfile
from collections import defaultdict
from functools import cmp_to_key
from typing import List, Tuple, Optional, Union, Dict, Collection
from typing import TypeVar

from redis import Redis
from rq import Queue, get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from rq.queue import EnqueueData

from api.config import REDIS_HOST, REDIS_PASS, FASTANI_MAX_PAIRWISE, \
    FASTANI_Q_NORMAL, FASTANI_Q_PRIORITY, FASTANI_PRIORITY_SECRET, FASTANI_BIN, FASTANI_JOB_TIMEOUT, \
    FASTANI_JOB_RESULT_TTL, FASTANI_JOB_FAIL_TTL, FASTANI_JOB_RETRY, FASTANI_GENOME_DIR
from api.exceptions import HttpBadRequest, HttpNotFound, HttpInternalServerError
from api.model.fastani import FastAniJobResult, FastAniParameters, FastAniResult, FastAniJobRequest, FastAniConfig, \
    FastAniResultData
from api.util.collection import x_prod, deduplicate
from api.util.ncbi import is_ncbi_accession


def get_fastani_config() -> FastAniConfig:
    return FastAniConfig(maxPairwise=FASTANI_MAX_PAIRWISE)


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

        if result.qvr.status is JobStatus.FINISHED and result.rvq.status is JobStatus.FINISHED:
            if result.qvr.ani and result.rvq.ani:
                ani = max(result.qvr.ani, result.rvq.ani)
                qvr_af = result.qvr.mapped / result.qvr.total
                rvq_af = result.rvq.mapped / result.rvq.total
                if qvr_af > rvq_af:
                    af = qvr_af
                    mapped = result.qvr.mapped
                    total = result.qvr.total
                else:
                    af = rvq_af
                    mapped = result.rvq.mapped
                    total = result.rvq.total
            elif result.qvr.ani:
                ani = result.qvr.ani
                af = result.qvr.mapped / result.qvr.total
                mapped = result.qvr.mapped
                total = result.qvr.total
            elif result.rvq.ani:
                ani = result.rvq.ani
                af = result.rvq.mapped / result.rvq.total
                mapped = result.rvq.mapped
                total = result.rvq.total
            else:
                ani = '< 80%'
                af = '-'
                mapped = '-'
                total = '-'
            status = JobStatus.FINISHED
        elif result.qvr.status == result.rvq.status:
            status = result.qvr.status
        else:
            status = 'not completed'

        out.append([
            result.query,
            result.reference,
            ani,
            af,
            mapped,
            total,
            status
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


T = TypeVar('T')


def get_existing_jobs(items: Collection[T], conn: Redis) -> Dict[T, Job]:
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

    # Create the job
    with Redis(host=REDIS_HOST, password=REDIS_PASS) as conn:
        q = Queue(FASTANI_Q_PRIORITY if is_priority else FASTANI_Q_NORMAL, connection=conn)

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
    tmp_results = defaultdict(lambda: defaultdict())
    for dependency in job.fetch_dependencies():
        q = dependency.meta.get('q')
        r = dependency.meta.get('r')
        stdout = dependency.meta.get('stdout')
        stderr = dependency.meta.get('stderr')
        cmd = dependency.meta.get('cmd')
        ani, mapped, total = None, None, None
        if dependency.result is not None:
            ani, mapped, total = dependency.result
        tmp_results[q][r] = FastAniResultData(ani=ani, mapped=mapped, total=total,
                                              status=JobStatus[dependency.get_status(refresh=False).upper()],
                                              stdout=stdout, stderr=stderr, cmd=cmd)

    # Group the results by query genome
    out = list()
    for query_gid in sorted(job.meta['group_1']):
        for ref_gid in sorted(job.meta['group_2']):
            qvr = tmp_results[query_gid][ref_gid]
            rvq = tmp_results[ref_gid][query_gid]
            out.append(FastAniResult(query=query_gid, reference=ref_gid, qvr=qvr, rvq=rvq))

    # Sort according to the sort parameters
    if sort_by and sort_desc and len(sort_by) == len(sort_desc):
        def sort_fn(a: FastAniResult, b: FastAniResult):
            a_ani, a_af, a_mapped, a_total, a_status = a.get_data()
            b_ani, b_af, b_mapped, b_total, b_status = b.get_data()

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

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        stdout, stderr = p.communicate()

        # Save output (as exceptions will return None)
        if job:
            job.meta['stderr'] = stderr
            job.meta['stdout'] = stdout
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


def get_unique_fastani_job_id(gid_a: str, gid_b: str, params: FastAniParameters):
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
