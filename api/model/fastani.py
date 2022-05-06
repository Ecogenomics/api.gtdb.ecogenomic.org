from typing import List, Optional, Literal

from pydantic import BaseModel, Field
from rq.job import JobStatus

VERSIONS = Literal['1.0', '1.1', '1.2', '1.3', '1.31', '1.32', '1.33']


class FastAniParameters(BaseModel):
    """All parameters that can be passed to FastANI."""
    kmer: int = Field(..., title="kmer size", ge=1, le=16, example=16)
    frag_len: int = Field(..., title="fragment length", ge=1, example=3000)
    min_frag: int = Field(..., title="minimum matched fragments for trusting ANI [versions <1.3]", ge=1, example=50)
    min_frac: float = Field(..., ge=0, le=1, example=0.2,
                            title="minimum fraction of genome that must be shared for trusting ANI [versions >=1.3]")
    version: VERSIONS = Field(..., example='1.33', title="which version of FastANI to use")


class FastAniResultData(BaseModel):
    """The data returned by FastANI."""
    ani: Optional[float] = Field(None, ge=0, le=100, example=90.9, title="percentage of ANI")
    af: Optional[float] = Field(None, ge=0, le=1, example=0.9, title="percentage of AF")
    mapped: Optional[int] = Field(None, ge=1, example=42, title="count of bidirectional fragment mappings")
    total: Optional[int] = Field(None, ge=1, example=100, title="total query fragments")
    status: JobStatus = Field(..., example=JobStatus.QUEUED.value, title="job processing status")
    stdout: Optional[str] = Field(None)
    stderr: Optional[str] = Field(None)
    cmd: Optional[str] = Field(None)


class FastAniResult(BaseModel):
    """The result of a single FastANI execution."""
    query: str = Field(..., example='GCA_123456789.1', title="GenBank or RefSeq accession")
    reference: str = Field(..., example='GCF_123456789.1', title="GenBank or RefSeq accession")
    data: FastAniResultData


class FastAniJobResult(BaseModel):
    """Represents a FastANI job request, this contains a list of results."""
    job_id: str = Field(..., example='c3710c6f-03ee-42f1-a01e-4c594619d605', title="unique ID associated with this job")
    group_1: List[str] = Field(..., example=['GCA_123456789.1'],
                               description='collection of GenBank/RefSeq accession(s)')
    group_2: List[str] = Field(..., example=['GCF_123456789.1'],
                               description='collection of GenBank/RefSeq accession(s)')
    parameters: FastAniParameters
    results: List[FastAniResult]
    positionInQueue: Optional[int] = Field(None)


class FastAniJobRequest(BaseModel):
    """The request sent by a user to run FastANI on the below parameters."""
    query: List[str] = Field(..., example=['GCA_123456789.1'], description='collection of GenBank/RefSeq accession(s)')
    reference: List[str] = Field(..., example=['GCF_123456789.1'],
                                 description='collection of GenBank/RefSeq accession(s)')
    parameters: FastAniParameters
    priority: str = Field(..., example='secret', title="secret key to use priority queue")


class FastAniConfig(BaseModel):
    """Returns the server-configured FastANI parameters."""
    maxPairwise: int = Field(..., example=1000, title="maximum number of pairwise comparisons")
