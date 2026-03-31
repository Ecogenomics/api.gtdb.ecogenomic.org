import os
from enum import Enum
from pathlib import Path

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
# Caching
# ------------------------------------------------------------------------------
CACHE_DIR: Path | None = Path(os.environ['CACHE_DIR']) if os.environ.get('CACHE_DIR') else None

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

FASTANI_DB_USER = os.environ.get('FASTANI_DB_USER')
FASTANI_DB_PASS = os.environ.get('FASTANI_DB_PASS')
FASTANI_DB_NAME = os.environ.get('FASTANI_DB_NAME')

# Maximum number of pairwise comparisons in a single job
FASTANI_MAX_PAIRWISE = 3000  # TODO: Remove
ANI_MAX_PAIRWISE = 500 ** 2
ANI_USER_MAX_FILE_SIZE_MB_EACH = 20
ANI_USER_MAX_FILE_COUNT = 10
ANI_USER_MAX_FILE_NAME_LENGTH = 200
ANI_QUEUE_MAX_PENDING_JOBS = 1000
ANI_JOB_ID_MAX_VALUE = 2 ** 32 - 1

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

# GTDB releases (the order must be preserved, with NCBI last)
GTDB_RELEASES = ('R80', 'R83', 'R86.2', 'R89', 'R95', 'R202', 'R207', 'R214', 'R220', 'R226', 'R232', 'NCBI')
CURRENT_RELEASE = 'R232'

SITEMAP_PAGES = [
    'about', 'advanced', 'attributions', 'browsers', 'contact', 'downloads', 'faq', 'gsc', 'methods', 'searches',
    'tools/ani', 'stats/r89', 'stats/r95', 'stats/r202', 'stats/r207', 'stats/r214', 'stats/r220', 'stats/r226',
    'stats/r232', 'taxon-history', 'tools', 'tree'
]

BAC120_MARKERS = frozenset({
    "PF00380.20", "PF00410.20", "PF00466.21",
    "PF01025.20", "PF02576.18", "PF03726.15",
    "TIGR00006", "TIGR00019", "TIGR00020",
    "TIGR00029", "TIGR00043", "TIGR00054",
    "TIGR00059", "TIGR00061", "TIGR00064",
    "TIGR00065", "TIGR00082", "TIGR00083",
    "TIGR00084", "TIGR00086", "TIGR00088",
    "TIGR00090", "TIGR00092", "TIGR00095",
    "TIGR00115", "TIGR00116", "TIGR00138",
    "TIGR00158", "TIGR00166", "TIGR00168",
    "TIGR00186", "TIGR00194", "TIGR00250",
    "TIGR00337", "TIGR00344", "TIGR00362",
    "TIGR00382", "TIGR00392", "TIGR00396",
    "TIGR00398", "TIGR00414", "TIGR00416",
    "TIGR00420", "TIGR00431", "TIGR00435",
    "TIGR00436", "TIGR00442", "TIGR00445",
    "TIGR00456", "TIGR00459", "TIGR00460",
    "TIGR00468", "TIGR00472", "TIGR00487",
    "TIGR00496", "TIGR00539", "TIGR00580",
    "TIGR00593", "TIGR00615", "TIGR00631",
    "TIGR00634", "TIGR00635", "TIGR00643",
    "TIGR00663", "TIGR00717", "TIGR00755",
    "TIGR00810", "TIGR00922", "TIGR00928",
    "TIGR00959", "TIGR00963", "TIGR00964",
    "TIGR00967", "TIGR01009", "TIGR01011",
    "TIGR01017", "TIGR01021", "TIGR01029",
    "TIGR01032", "TIGR01039", "TIGR01044",
    "TIGR01059", "TIGR01063", "TIGR01066",
    "TIGR01071", "TIGR01079", "TIGR01082",
    "TIGR01087", "TIGR01128", "TIGR01146",
    "TIGR01164", "TIGR01169", "TIGR01171",
    "TIGR01302", "TIGR01391", "TIGR01393",
    "TIGR01394", "TIGR01510", "TIGR01632",
    "TIGR01951", "TIGR01953", "TIGR02012",
    "TIGR02013", "TIGR02027", "TIGR02075",
    "TIGR02191", "TIGR02273", "TIGR02350",
    "TIGR02386", "TIGR02397", "TIGR02432",
    "TIGR02729", "TIGR03263", "TIGR03594",
    "TIGR03625", "TIGR03632", "TIGR03654",
    "TIGR03723", "TIGR03725", "TIGR03953"
})

AR53_MARKERS = frozenset({
    "TIGR00037", "TIGR00064", "TIGR00111",
    "TIGR00134", "TIGR00279", "TIGR00291", "TIGR00323",
    "TIGR00335", "TIGR00373", "TIGR00405", "TIGR00448",
    "TIGR00483", "TIGR00491", "TIGR00522", "TIGR00967",
    "TIGR00982", "TIGR01008", "TIGR01012", "TIGR01018",
    "TIGR01020", "TIGR01028", "TIGR01046", "TIGR01052",
    "TIGR01171", "TIGR01213", "TIGR01952", "TIGR02236",
    "TIGR02338", "TIGR02389", "TIGR02390", "TIGR03626",
    "TIGR03627", "TIGR03628", "TIGR03629", "TIGR03670",
    "TIGR03671", "TIGR03672", "TIGR03673", "TIGR03674",
    "TIGR03676", "TIGR03680", "PF04919.13", "PF07541.13", "PF01000.27",
    "PF00687.22", "PF00466.21", "PF00827.18", "PF01280.21", "PF01090.20",
    "PF01200.19", "PF01015.19", "PF00900.21", "PF00410.20"
})
