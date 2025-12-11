from enum import Enum
from typing import List, Literal, Optional

import numpy as np
from pydantic import BaseModel, Field

from api.config import (
    ANI_MAX_PAIRWISE, ANI_QUEUE_MAX_PENDING_JOBS, ANI_USER_MAX_FILE_COUNT, ANI_USER_MAX_FILE_NAME_LENGTH,
    ANI_USER_MAX_FILE_SIZE_MB_EACH
)
from api.exceptions import HttpBadRequest
from api.util.common import is_valid_email


# Enum types

class SkaniVersion(str, Enum):
    SKANI_0_3_0 = "0.3.0"


class SkaniParametersPreset(str, Enum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SMALL_GENOMES = "small-genomes"


class SkaniDeleteUserResultsAfter(str, Enum):
    DISABLED = "disabled"
    HOUR_1 = "1_hour"
    DAY_1 = "1_day"
    WEEK_1 = "1_week"
    MONTH_1 = "1_month"


class SkaniCalculationMode(str, Enum):
    QVR = "Query vs. Reference"
    TRIANGLE = "Triangle"


# Pydantic classes

class SkaniServerConfig(BaseModel):
    """The server configuration for jobs relating to skani."""
    maxPairwise: int = Field(
        ANI_MAX_PAIRWISE,
        description='maximum number of pairwise comparisons allowed in a single job'
    )
    maxUserFileSizeMbEach: int = Field(
        ANI_USER_MAX_FILE_SIZE_MB_EACH,
        description='maximum size (in MB) of each user genome file that can be uploaded'
    )
    maxUserFileNameLength: int = Field(
        ANI_USER_MAX_FILE_NAME_LENGTH,
        description='maximum length of each file name that can be uploaded'
    )
    maxUserFileCount: int = Field(
        ANI_USER_MAX_FILE_COUNT,
        description='maximum number of user genome files that can be uploaded'
    )
    supportedPrograms: List[SkaniVersion] = Field(
        list(SkaniVersion),
        description='list of supported versions'
    )
    maxQueuePendingJobs: int = Field(
        ANI_QUEUE_MAX_PENDING_JOBS,
        description='maximum number of pending jobs allowed in the queue'
    )


class SkaniParameters(BaseModel):
    """All parameters that can be passed to skani."""
    minAf: float | None = Field(
        ...,
        examples=[None],
        title="Only output ANI values where one genome has aligned fraction > than this value. [default: 15]"
    )
    bothMinAf: float | None = Field(
        ...,
        examples=[None],
        title="Only output ANI values where both genomes have aligned fraction > than this value. [default: disabled]"
    )
    skaniPreset: SkaniParametersPreset | None = Field(
        ...,
        examples=[None],
        title="Preset mode selection."
    )
    cFactor: int | None = Field(
        ...,
        ge=0,
        examples=[None],
        title="Compression factor (k-mer subsampling rate). [default: 125]"
    )
    fasterSmall: bool | None = Field(
        ...,
        examples=[None],
        title="Filter genomes with < 20 marker k-mers more aggressively. Much faster for many small genomes but may miss some comparisons."
    )
    mFactor: int | None = Field(
        ...,
        ge=0,
        examples=[None],
        title="Marker k-mer compression factor. Markers are used for filtering. Consider decreasing to ~200-300 if working with small genomes (e.g. plasmids or viruses). [default: 1000]"
    )
    useMedian: bool | None = Field(
        ...,
        examples=[None],
        title="Estimate median identity instead of average (mean) identity."
    )
    noLearnedAni: bool | None = Field(
        ...,
        examples=[None],
        title="Disable regression model for ANI prediction. [default: learned ANI used for c >= 70 and >= 150,000 bases aligned and not on individual contigs."
    )
    noMarkerIndex: bool | None = Field(
        ...,
        examples=[None],
        title="Do not use hash-table inverted index for faster ANI filtering. [default: load index if > 100 query files or using the --qi option]"
    )
    robust: bool | None = Field(
        ...,
        examples=[None],
        title="Estimate mean after trimming off 10%/90% quantiles."
    )
    screen: float | None = Field(
        ...,
        examples=[None],
        title="Screen out pairs with *approximately* < % identity using k-mer sketching. [default: 80]"
    )

    def all_params_null(self) -> bool:
        return all(
            [
                self.minAf is None,
                self.bothMinAf is None,
                self.skaniPreset is None,
                self.cFactor is None,
                self.fasterSmall is None,
                self.mFactor is None,
                self.useMedian is None,
                self.noLearnedAni is None,
                self.noMarkerIndex is None,
                self.robust is None,
                self.screen is None,
            ]
        )

    def sanitise_for_version(self, version: SkaniVersion, calc_mode: SkaniCalculationMode):
        """Remove parameters that are not used by the specific program & version."""

        if calc_mode is SkaniCalculationMode.TRIANGLE:
            self.noMarkerIndex = None

        # If a preset has been selected, then remove the corresponding values
        if version is SkaniVersion.SKANI_0_3_0:
            if self.skaniPreset in {
                SkaniParametersPreset.FAST, SkaniParametersPreset.MEDIUM, SkaniParametersPreset.SLOW
            }:
                self.cFactor = None
            elif self.skaniPreset is SkaniParametersPreset.SMALL_GENOMES:
                self.cFactor = None
                self.mFactor = None
                self.fasterSmall = None

        # Set version-specific default values to None
        if version is SkaniVersion.SKANI_0_3_0:
            if self.minAf == 15:
                self.minAf = None
            if self.cFactor == 125:
                self.cFactor = None
            if self.mFactor == 1000:
                self.mFactor = None
            if self.screen == 80:
                self.screen = None


class SkaniJobUploadMetadata(BaseModel):
    """The supplemental request body that is used when users upload files."""
    fileNames: List[str] = Field(..., description='A list of all file names provided.')
    deleteAfter: SkaniDeleteUserResultsAfter | None = Field(
        ..., description='Delete results for this request after this time period.'
    )


class SkaniJobRequest(BaseModel):
    """The request body used to create an ANI job."""
    query: list[str] = Field(
        ...,
        examples=[['GCA_123456789.1']],
        description='collection of GenBank/RefSeq query accession(s)'
    )
    reference: list[str] = Field(
        ...,
        examples=[['GCF_123456789.1']],
        description='collection of GenBank/RefSeq reference accession(s)'
    )
    params: SkaniParameters | None = Field(None, description='parameters to run the program')
    email: str | None = Field(None, examples=['foo@bar.com'], title="e-mail address to be notified on completion")
    calcMode: SkaniCalculationMode = Field(..., title="The calculation mode to run.")
    version: SkaniVersion = Field(..., title="Program version to use.")

    def validate_email(self):
        if self.email is not None and len(self.email) > 3:
            if not is_valid_email(self.email):
                raise HttpBadRequest('The e-mail address is invalid.')

    def validate_parameters(self, calc_mode: SkaniCalculationMode):
        if self.params is not None:
            self.params.sanitise_for_version(self.version, calc_mode)
            if self.params.all_params_null():
                self.params = None


class SkaniValidateGenomesRequest(BaseModel):
    genomes: list[str] = Field(
        ...,
        examples=[['GCA_123456789.1']],
        description='collection of GenBank/RefSeq query accession(s)'
    )


class SkaniValidateGenomesResponse(BaseModel):
    accession: str = Field(..., examples=['GCA_123456789.1'], title="GenBank or RefSeq accession")
    isUser: bool = Field(False)
    isSpRep: Optional[bool] = Field(None, examples=[True], title="is this genome a GTDB representative genome")
    gtdbDomain: Optional[str] = Field(None, examples=['d__Domain'], title="GTDB domain")
    gtdbPhylum: Optional[str] = Field(None, examples=['p__Phylum'], title="GTDB phylum")
    gtdbClass: Optional[str] = Field(None, examples=['c__Class'], title="GTDB class")
    gtdbOrder: Optional[str] = Field(None, examples=['o__Order'], title="GTDB order")
    gtdbFamily: Optional[str] = Field(None, examples=['f__Family'], title="GTDB family")
    gtdbGenus: Optional[str] = Field(None, examples=['g__Genus'], title="GTDB genus")
    gtdbSpecies: Optional[str] = Field(None, examples=['s__Species'], title="GTDB species")


class SkaniJobDataIndexResponse(BaseModel):
    jobId: str = Field(...)
    params: SkaniParameters | None = Field(...)
    mode: SkaniCalculationMode = Field(...)
    version: SkaniVersion
    query: list[SkaniValidateGenomesResponse]
    reference: list[SkaniValidateGenomesResponse]


class SkaniCreatedJobResponse(BaseModel):
    """The response returned when a new job is created."""
    jobId: str = Field(..., title='The id of the job that was created.')


class SkaniResultTableRow(BaseModel):
    qry: str = Field(...)
    ref: str = Field(...)
    ani: float | None = Field(None)
    afQry: float | None = Field(None)
    afRef: float | None = Field(None)

    @staticmethod
    def get_column_names() -> List[str]:
        return ['query', 'reference', 'ani', 'af_query', 'af_reference']

    def to_row(self):
        return [self.qry, self.ref, self.ani, self.afQry, self.afRef]



class SkaniJobDataTableResponse(BaseModel):
    jobId: str = Field(...)
    completed: bool = Field(...)
    error: bool | None = Field(...)
    # totalResults: int = Field(...)
    # totalPages: int = Field(...)
    rows: List[SkaniResultTableRow] = Field(...)


class SkaniJobStatusResponse(BaseModel):
    jobId: str = Field(...)
    createdEpoch: int = Field(...)
    completedEpoch: int | None = Field(...)
    error: bool | None = Field(...)
    positionInQueue: int | None = Field(...)
    totalPendingJobs: int | None = Field(...)
    stdout: str | None = Field(...)
    stderr: str | None = Field(...)
    deleteAfter: SkaniDeleteUserResultsAfter | None = Field(...)


class SkaniJobHeatmapData(BaseModel):
    x: int = Field(...)
    y: int = Field(...)
    ani: float = Field(...)
    af: float = Field(...)


class SkaniJobDataHeatmapResponse(BaseModel):
    jobId: str = Field(...)
    completed: bool = Field(...)

    ani: list[list[float]] = Field(..., )
    af: list[list[float]] = Field(..., )
    xLabels: list[str] = Field(..., )
    yLabels: list[str] = Field(..., )
    xSpecies: list[str] = Field(..., )
    ySpecies: list[str] = Field(..., )
    method: Literal['ani', 'af'] = Field(..., )
    spReps: list[str] = Field(..., )


class UtilSkaniJobResults(BaseModel):
    qry_ids: list[int]
    ref_ids: list[int]
    ani: np.ndarray
    af_qry: np.ndarray
    af_ref: np.ndarray

    class Config:
        arbitrary_types_allowed = True
