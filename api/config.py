import os
from enum import Enum

from rq import Retry


# ------------------------------------------------------------------------------
# Determine which environment the API is running in
# ------------------------------------------------------------------------------

class Env(Enum):
    PROD = 'prod'
    DEV = 'dev'
    LOCAL = 'local'


ENV_NAME = Env[os.environ.get('ENV_NAME', 'local').upper()]

# ------------------------------------------------------------------------------
# PostgreSQL
# ------------------------------------------------------------------------------

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', '')
POSTGRES_USER = os.environ.get('POSTGRES_USER', '')
POSTGRES_PASS = os.environ.get('POSTGRES_PASS', '')

# ------------------------------------------------------------------------------
# RedisQueue
# ------------------------------------------------------------------------------

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PASS = os.environ.get('REDIS_PASS', '')

# ------------------------------------------------------------------------------
# CAPTCHA
# ------------------------------------------------------------------------------

GTDB_CAPTCHA_SECRET_KEY = os.environ.get('GTDB_CAPTCHA_SECRET_KEY', '')

# ------------------------------------------------------------------------------
# SMTP
# ------------------------------------------------------------------------------

SMTP_FROM = os.environ.get('SMTP_FROM', '')
SMTP_SERV = os.environ.get('SMTP_SERV', '')
SMTP_PORT = os.environ.get('SMTP_PORT', '')
SMTP_TIMEOUT = os.environ.get('SMTP_TIMEOUT', '')
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')

SMTP_DOMAIN_BLACKLIST = {'aneesho.com'}

# ------------------------------------------------------------------------------
# FastANI
# ------------------------------------------------------------------------------

# Supported versions and their paths
FASTANI_BIN = {
    '1.0': '/bin/fastANI_1.0',
    '1.1': '/bin/fastANI_1.1',
    '1.2': '/bin/fastANI_1.2',
    '1.3': '/bin/fastANI_1.3',
    '1.31': '/bin/fastANI_1.31',
    '1.32': '/bin/fastANI_1.32',
    '1.33': '/bin/fastANI_1.33'
}

# Used to assign jobs to a priority queue
FASTANI_PRIORITY_SECRET = os.environ.get('FASTANI_PRIORITY_SECRET')

# These queues contain individual FastANI jobs
FASTANI_Q_PRIORITY = os.environ.get('FASTANI_Q_PRIORITY', 'website-fastani-priority')
FASTANI_Q_NORMAL = os.environ.get('FASTANI_Q_NORMAL', 'website-fastani-normal')
FASTANI_Q_LOW = os.environ.get('FASTANI_Q_LOW', 'website-fastani-low')

# Maximum number of pairwise comparisons in a single job
FASTANI_MAX_PAIRWISE = 1000
FASTANI_MAX_PAIRWISE_LOW = 10_000

# Maximum runtime before job is marked as failed (seconds)
FASTANI_JOB_TIMEOUT = '10m'

# Successful jobs are kept for this long
FASTANI_JOB_RESULT_TTL = '30d'

# Failed jobs are kept for this many seconds
FASTANI_JOB_FAIL_TTL = '1d'

# Retry strategy for FastANI jobs
FASTANI_JOB_RETRY = Retry(max=3)

# Root directory where all NCBI genomes exist
FASTANI_GENOME_DIR = os.environ.get('FASTANI_GENOME_DIR')

# GTDB releases
GTDB_RELEASES = ('R80', 'R83', 'R86.2', 'R89', 'R95', 'R202', 'R207', 'NCBI')
