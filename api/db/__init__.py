from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine

from api.config import POSTGRES_USER, POSTGRES_PASS, POSTGRES_HOST, FASTANI_DB_USER, FASTANI_DB_PASS, FASTANI_DB_NAME

GTDB_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/gtdb_r226'
GTDB_WEB_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/gtdb_r226_web'
GTDB_COMMON_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/common'
GTDB_FASTANI_DB_URL = f'postgresql://{FASTANI_DB_USER}:{FASTANI_DB_PASS}@{POSTGRES_HOST}/{FASTANI_DB_NAME}'

gtdb_engine = create_engine(
    GTDB_DB_URL,
    pool_size=10,
    max_overflow=100,
    pool_recycle=3600
)

gtdb_web_engine = create_engine(
    GTDB_WEB_DB_URL,
    pool_size=10,
    max_overflow=100,
    pool_recycle=3600
)

gtdb_common_engine = create_engine(
    GTDB_COMMON_DB_URL,
    pool_size=10,
    max_overflow=100,
    pool_recycle=3600
)

gtdb_fastani_engine = create_engine(
    GTDB_FASTANI_DB_URL,
    pool_size=10,
    max_overflow=100,
    pool_recycle=3600
)


def get_gtdb_db():
    with Session(gtdb_engine) as session:
        yield session


def get_gtdb_web_db():
    with Session(gtdb_web_engine) as session:
        yield session


def get_gtdb_common_db():
    with Session(gtdb_common_engine) as session:
        yield session


def get_gtdb_fastani_db():
    with Session(gtdb_fastani_engine) as session:
        yield session


GtdbDbDep = Annotated[Session, Depends(get_gtdb_db)]
GtdbWebDbDep = Annotated[Session, Depends(get_gtdb_web_db)]
GtdbCommonDbDep = Annotated[Session, Depends(get_gtdb_common_db)]
GtdbFastAniDbDep = Annotated[Session, Depends(get_gtdb_fastani_db)]
