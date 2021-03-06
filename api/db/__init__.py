from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from api.config import POSTGRES_USER, POSTGRES_PASS, POSTGRES_HOST

GTDB_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/gtdb_r207'
GTDB_WEB_DB_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/gtdb_r207_web'

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

GtdbSession = sessionmaker(autocommit=False, autoflush=False, bind=gtdb_engine)
GtdbWebSession = sessionmaker(autocommit=False, autoflush=False, bind=gtdb_web_engine)

GtdbBase = declarative_base()
GtdbWebBase = declarative_base()


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
