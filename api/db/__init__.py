from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from api.config import POSTGRES_USER, POSTGRES_PASS, POSTGRES_HOST

GTDB_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/gtdb_r214'
GTDB_WEB_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/gtdb_r214_web'
GTDB_COMMON_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/common'

gtdb_engine = create_engine(
    GTDB_DB_URL,
    convert_unicode=True,
    pool_size=5,
    max_overflow=20,
    pool_recycle=3600
)

gtdb_web_engine = create_engine(
    GTDB_WEB_DB_URL,
    convert_unicode=True,
    pool_size=5,
    max_overflow=20,
    pool_recycle=3600
)

gtdb_common_engine = create_engine(
    GTDB_COMMON_DB_URL,
    convert_unicode=True,
    pool_size=5,
    max_overflow=20,
    pool_recycle=3600
)

GtdbSession = sessionmaker(autocommit=False, autoflush=False, bind=gtdb_engine)
GtdbWebSession = sessionmaker(autocommit=False, autoflush=False, bind=gtdb_web_engine)
GtdbCommonSession = sessionmaker(autocommit=False, autoflush=False, bind=gtdb_common_engine)

GtdbBase = declarative_base()
GtdbWebBase = declarative_base()
GtdbCommonBase = declarative_base()


def get_gtdb_db():
    db = GtdbSession()
    try:
        yield db
    finally:
        db.close()


def get_gtdb_web_db():
    db = GtdbWebSession()
    try:
        yield db
    finally:
        db.close()


def get_gtdb_common_db():
    db = GtdbCommonSession()
    try:
        yield db
    finally:
        db.close()
