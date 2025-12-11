from datetime import datetime

import sqlalchemy as sa
import sqlmodel as sm
from sqlmodel import ARRAY, CHAR, Column, Field, SMALLINT, SQLModel, TIMESTAMP

from api.model.skani import SkaniCalculationMode, SkaniDeleteUserResultsAfter, SkaniParametersPreset, SkaniVersion

"""
Tables below.
"""


class DbGenomesOnDisk(SQLModel, table=True):
    __tablename__ = 'genomes_on_disk'

    id: int | None = Field(primary_key=True, default=None)
    name: str = Field(sa_column=Column(CHAR(15), nullable=False))
    fna_gz_md5: str = Field(sa_column=Column(CHAR(32), nullable=False))
    assembly_url: str | None = Field()


class DbSkaniGenome(SQLModel, table=True):
    __tablename__ = 'genome'
    __table_args__ = {'schema': 'skani'}

    id: int = Field(sa_column=Column(sa.Integer, sa.Identity(), primary_key=True, autoincrement=True))
    ncbi_id: int | None = Field(foreign_key='genomes_on_disk.id', nullable=True)
    user_id: str = Field(foreign_key='skani.user_genome.id', nullable=False)


class DbSkaniJob(SQLModel, table=True):
    __tablename__ = 'job'
    __table_args__ = {'schema': 'skani'}

    id: int = Field(sa_column=Column(sa.Integer, sa.Identity(), primary_key=True, autoincrement=True))
    param_id: int = Field(foreign_key='skani.param.id', nullable=False)
    created: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=sm.func.now()))
    email: str | None = Field()
    email_sent: datetime | None = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=True))
    completed: datetime | None = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=True))
    error: bool | None = Field(nullable=True)
    delete_after: SkaniDeleteUserResultsAfter | None = Field(nullable=True)
    mode: SkaniCalculationMode | None = Field(nullable=True)
    stdout: str | None = Field(nullable=True)
    stderr: str | None = Field(nullable=True)
    name: str = Field(nullable=False)
    deleted: bool = Field(nullable=False, default=False)
    ready: bool = Field(nullable=False, default=False)
    delete_after_ts: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=True))


class DbSkaniJobQuery(SQLModel, table=True):
    __tablename__ = 'job_query'
    __table_args__ = {'schema': 'skani'}

    job_id: int = Field(primary_key=True, foreign_key='skani.job.id', nullable=False)
    genome_id: int = Field(primary_key=True, foreign_key='skani.genome.id', nullable=False)


class DbSkaniJobReference(SQLModel, table=True):
    __tablename__ = 'job_reference'
    __table_args__ = {'schema': 'skani'}

    job_id: int = Field(primary_key=True, foreign_key='skani.job.id', nullable=False)
    genome_id: int = Field(primary_key=True, foreign_key='skani.genome.id', nullable=False)


class DbSkaniParam(SQLModel, table=True):
    __tablename__ = 'param'
    __table_args__ = {'schema': 'skani'}

    id: int = Field(sa_column=Column(sa.Integer, sa.Identity(), primary_key=True, autoincrement=True))
    version: SkaniVersion = Field(nullable=False)
    min_af: float | None = Field(nullable=True)
    both_min_af: float | None = Field(nullable=True)
    preset: SkaniParametersPreset | None = Field(nullable=True)
    c: int | None = Field(nullable=True)
    faster_small: bool = Field(nullable=False, default=False)
    m: int | None = Field(nullable=True)
    median: bool = Field(nullable=False, default=False)
    no_learned_ani: bool = Field(nullable=False, default=False)
    no_marker_index: bool = Field(nullable=False, default=False)
    robust: bool = Field(nullable=False, default=False)
    s: float | None = Field(nullable=True)


class DbSkaniResult(SQLModel, table=True):
    __tablename__ = 'result'
    __table_args__ = {'schema': 'skani'}

    id: int = Field(sa_column=Column(sa.Integer, sa.Identity(), primary_key=True, autoincrement=True))
    param_id: int = Field(foreign_key='skani.program.id', nullable=False)
    qry_id: int | None = Field(foreign_key='skani.genome.id', nullable=True)
    ref_id: int | None = Field(foreign_key='skani.genome.id', nullable=True)
    ani: float | None = Field(nullable=True)
    af_ref: float | None = Field(nullable=True)
    af_qry: float | None = Field(nullable=True)


class DbSkaniUserGenome(SQLModel, table=True):
    __tablename__ = 'user_genome'
    __table_args__ = {'schema': 'skani'}

    id: int = Field(sa_column=Column(sa.Integer, sa.Identity(), primary_key=True, autoincrement=True))
    job_id: int = Field(foreign_key='skani.job.id', nullable=False)
    file_name: str = Field(nullable=False)
    fna: str | None = Field(nullable=True)


class DbSkaniJobResult(SQLModel, table=True):
    __tablename__ = 'job_result'
    __table_args__ = {'schema': 'skani'}

    job_id: int = Field(primary_key=True, foreign_key='skani.job.id', nullable=False)
    ani: list[int] = Field(sa_column=Column(ARRAY(SMALLINT)))
    af_qry: list[int] = Field(sa_column=Column(ARRAY(SMALLINT)))
    af_ref: list[int] = Field(sa_column=Column(ARRAY(SMALLINT)))
