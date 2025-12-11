from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, Json

from api.config import ANI_USER_MAX_FILE_SIZE_MB_EACH, ANI_USER_MAX_FILE_COUNT, ANI_MAX_PAIRWISE, \
    ANI_USER_MAX_FILE_NAME_LENGTH, ANI_QUEUE_MAX_PENDING_JOBS
from api.exceptions import HttpBadRequest
from api.util.common import is_valid_email
from api.util.io import string_size_in_mb

SKANI_NAME = "skani"


class AniProgramEnum(Enum):
    SKANI_0_3_0 = (SKANI_NAME, "0.3.0")


class AniProgram(BaseModel):
    name: str = Field(..., description='The name of the program used', example='skani')
    version: str = Field(..., description='The version of the program used', example='0.3.0')

    def to_enum(self) -> AniProgramEnum:
        if self.name == "skani" and self.version == "0.3.0":
            return AniProgramEnum.SKANI_0_3_0
        raise HttpBadRequest(f"Unable to convert {self.name} v{self.version} to enum")


ANI_PROGRAM_LIST = (AniProgram(name=x.value[0], version=x.value[1]) for x in AniProgramEnum)


class AniGenomeValidationResponse(BaseModel):
    """Validates that the genomes are suitable for ANI (i.e. in database)."""
    accession: str = Field(..., example='GCA_123456789.1', title="GenBank or RefSeq accession")
    isSpRep: Optional[bool] = Field(None, example=True, title="is this genome a GTDB representative genome")
    gtdbDomain: Optional[str] = Field(None, example='d__Domain', title="GTDB domain")
    gtdbPhylum: Optional[str] = Field(None, example='p__Phylum', title="GTDB phylum")
    gtdbClass: Optional[str] = Field(None, example='c__Class', title="GTDB class")
    gtdbOrder: Optional[str] = Field(None, example='o__Order', title="GTDB order")
    gtdbFamily: Optional[str] = Field(None, example='f__Family', title="GTDB family")
    gtdbGenus: Optional[str] = Field(None, example='g__Genus', title="GTDB genus")
    gtdbSpecies: Optional[str] = Field(None, example='s__Species', title="GTDB species")


class AniGenomeValidationRequest(BaseModel):
    """Validates that the genomes are suitable for ANI (i.e. in database)."""
    genomes: List[str] = Field(..., example=['GCA_123456789.1', 'GCF_123456789.1'])


class SkaniParametersPreset(Enum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SMALL_GENOMES = "small-genomes"


class AniParametersFastAni(BaseModel):
    """All possible parameters for all supported FastANI versions."""
    fastAniKmer: Optional[int] = Field(..., title="kmer size", ge=1, le=16, example=16)
    fastAniFragLen: Optional[int] = Field(..., title="fragment length", ge=1, example=3000)
    fastAniMinFrag: Optional[int] = Field(..., title="minimum matched fragments for trusting ANI [versions <1.3]", ge=1,
                                          example=50)
    fastAniMinFrac: Optional[int] = Field(..., ge=0, le=1, example=0.2,
                                          title="minimum fraction of genome that must be shared for trusting ANI [versions >=1.3]")

    def all_params_null(self) -> bool:
        return all([
            self.fastAniKmer is None,
            self.fastAniFragLen is None,
            self.fastAniMinFrag is None,
            self.fastAniMinFrac is None
        ])

    def sanitise_for_program(self, program: AniProgram):
        """Remove parameters that are not used by the specific program & version."""
        program_enum = program.to_enum()

        # Perform version-specific filtering
        if program_enum in {AniProgramEnum.FASTANI_1_0, AniProgramEnum.FASTANI_1_1, AniProgramEnum.FASTANI_1_2}:
            self.fastAniMinFrac = None
        else:
            self.fastAniMinFrag = None


class AniParametersSkani(BaseModel):
    """All possible parameters for all supported skani versions."""
    skaniMinAf: Optional[float] = Field(...,
                                        title="Only output ANI values where one genome has aligned fraction > than this value. [default: 15]")
    skaniBothMinAf: Optional[float] = Field(...,
                                            title="Only output ANI values where both genomes have aligned fraction > than this value. [default: disabled]")
    skaniPreset: Optional[SkaniParametersPreset] = Field(..., title="Preset mode selection.")
    skaniCFactor: Optional[int] = Field(..., ge=0, title="Compression factor (k-mer subsampling rate). [default: 125]")
    skaniFasterSmall: Optional[bool] = Field(...,
                                             title="Filter genomes with < 20 marker k-mers more aggressively. Much faster for many small genomes but may miss some comparisons.")
    skaniMFactor: Optional[int] = Field(..., ge=0,
                                        title="Marker k-mer compression factor. Markers are used for filtering. Consider decreasing to ~200-300 if working with small genomes (e.g. plasmids or viruses). [default: 1000]")
    skaniUseMedian: Optional[bool] = Field(..., title="Estimate median identity instead of average (mean) identity.")
    skaniNoLearnedAni: Optional[bool] = Field(...,
                                              title="Disable regression model for ANI prediction. [default: learned ANI used for c >= 70 and >= 150,000 bases aligned and not on individual contigs.")
    skaniNoMarkerIndex: Optional[bool] = Field(...,
                                               title="Do not use hash-table inverted index for faster ANI filtering. [default: load index if > 100 query files or using the --qi option]")
    skaniRobust: Optional[bool] = Field(..., title="Estimate mean after trimming off 10%/90% quantiles.")
    skaniScreen: Optional[float] = Field(...,
                                         title="Screen out pairs with *approximately* < % identity using k-mer sketching. [default: 80]")
    skaniDetailed: Optional[bool] = Field(..., title="Print additional info including contig N50s and more")

    def all_params_null(self) -> bool:
        return all([
            self.skaniMinAf is None,
            self.skaniBothMinAf is None,
            self.skaniPreset is None,
            self.skaniCFactor is None,
            self.skaniFasterSmall is None,
            self.skaniMFactor is None,
            self.skaniUseMedian is None,
            self.skaniNoLearnedAni is None,
            self.skaniNoMarkerIndex is None,
            self.skaniRobust is None,
            self.skaniScreen is None,
            self.skaniDetailed is None
        ])

    def sanitise_for_program(self, program: AniProgram):
        """Remove parameters that are not used by the specific program & version."""
        program_enum = program.to_enum()

        # Nullify those parameters that are not used by this program
        if program.name == SKANI_NAME:

            # Perform version-specific filtering

            # If a preset has been selected, then remove the corresponding values
            if program_enum is AniProgramEnum.SKANI_0_3_0:
                if self.skaniPreset in {SkaniParametersPreset.FAST, SkaniParametersPreset.MEDIUM,
                                        SkaniParametersPreset.SLOW}:
                    self.skaniCFactor = None
                elif self.skaniPreset is SkaniParametersPreset.SMALL_GENOMES:
                    self.skaniCFactor = None
                    self.skaniMFactor = None
                    self.skaniFasterSmall = None

            # Set version-specific default values to None
            if program_enum is AniProgramEnum.SKANI_0_3_0:
                if self.skaniMinAf == 15:
                    self.skaniMinAf = None
                if self.skaniCFactor == 125:
                    self.skaniCFactor = None
                if self.skaniMFactor == 1000:
                    self.skaniMFactor = None
                if self.skaniScreen == 80:
                    self.skaniScreen = None


class AniParameterJson(BaseModel):
    """All possible parameters for all supported programs (will be filtered server side)."""

    # fastani
    fastAniKmer: Optional[int] = Field(..., title="kmer size", ge=1, le=16, example=16)
    fastAniFragLen: Optional[int] = Field(..., title="fragment length", ge=1, example=3000)
    fastAniMinFrag: Optional[int] = Field(..., title="minimum matched fragments for trusting ANI [versions <1.3]", ge=1,
                                          example=50)
    fastAniMinFrac: Optional[int] = Field(..., ge=0, le=1, example=0.2,
                                          title="minimum fraction of genome that must be shared for trusting ANI [versions >=1.3]")

    # skani
    skaniMinAf: Optional[float] = Field(...,
                                        title="Only output ANI values where one genome has aligned fraction > than this value. [default: 15]")
    skaniBothMinAf: Optional[float] = Field(...,
                                            title="Only output ANI values where both genomes have aligned fraction > than this value. [default: disabled]")
    skaniPreset: Optional[SkaniParametersPreset] = Field(..., title="Preset mode selection.")
    skaniCFactor: Optional[int] = Field(..., ge=0, title="Compression factor (k-mer subsampling rate). [default: 125]")
    skaniFasterSmall: Optional[bool] = Field(...,
                                             title="Filter genomes with < 20 marker k-mers more aggressively. Much faster for many small genomes but may miss some comparisons.")
    skaniMFactor: Optional[int] = Field(..., ge=0,
                                        title="Marker k-mer compression factor. Markers are used for filtering. Consider decreasing to ~200-300 if working with small genomes (e.g. plasmids or viruses). [default: 1000]")
    skaniUseMedian: Optional[bool] = Field(..., title="Estimate median identity instead of average (mean) identity.")
    skaniNoLearnedAni: Optional[bool] = Field(...,
                                              title="Disable regression model for ANI prediction. [default: learned ANI used for c >= 70 and >= 150,000 bases aligned and not on individual contigs.")
    skaniNoMarkerIndex: Optional[bool] = Field(...,
                                               title="Do not use hash-table inverted index for faster ANI filtering. [default: load index if > 100 query files or using the --qi option]")
    skaniRobust: Optional[bool] = Field(..., title="Estimate mean after trimming off 10%/90% quantiles.")
    skaniScreen: Optional[float] = Field(...,
                                         title="Screen out pairs with *approximately* < % identity using k-mer sketching. [default: 80]")

    def sanitise_for_program(self, program: AniProgram):
        """Remove parameters that are not used by the specific program & version."""
        program_enum = program.to_enum()

        # Nullify those parameters that are not used by this program
        if program.name == SKANI_NAME:
            self.fastAniKmer = None
            self.fastAniFragLen = None
            self.fastAniMinFrag = None
            self.fastAniMinFrac = None

            # Perform version-specific filtering

            # If a preset has been selected, then remove the corresponding values
            if program_enum is AniProgramEnum.SKANI_0_3_0:
                if self.skaniPreset in {SkaniParametersPreset.FAST, SkaniParametersPreset.MEDIUM,
                                        SkaniParametersPreset.SLOW}:
                    self.skaniCFactor = None
                elif self.skaniPreset is SkaniParametersPreset.SMALL_GENOMES:
                    self.skaniCFactor = None
                    self.skaniMFactor = None
                    self.skaniFasterSmall = None

            # Set version-specific default values to None
            if program_enum is AniProgramEnum.SKANI_0_3_0:
                if self.skaniMinAf == 15:
                    self.skaniMinAf = None
                if self.skaniCFactor == 125:
                    self.skaniCFactor = None
                if self.skaniMFactor == 1000:
                    self.skaniMFactor = None
                if self.skaniScreen == 80:
                    self.skaniScreen = None

        elif program.name == FASTANI_NAME:
            self.skaniMinAf = None
            self.skaniBothMinAf = None
            self.skaniPreset = None
            self.skaniCFactor = None
            self.skaniFasterSmall = None
            self.skaniMFactor = None
            self.skaniUseMedian = None
            self.skaniNoLearnedAni = None
            self.skaniNoMarkerIndex = None
            self.skaniRobust = None
            self.skaniScreen = None

            # Perform version-specific filtering
            if program_enum in {AniProgramEnum.FASTANI_1_0, AniProgramEnum.FASTANI_1_1, AniProgramEnum.FASTANI_1_2}:
                self.fastAniMinFrac = None
            else:
                self.fastAniMinFrag = None

        else:
            raise HttpBadRequest(f'The program name {program.name} is not defined.')


class AniResult(BaseModel):
    query: str = Field(..., example='GCA_123456789.1', title="query GenBank or RefSeq accession")
    reference: str = Field(..., example='GCF_123456789.1', title="reference GenBank or RefSeq accession")
    ani: Optional[float] = Field(None, ge=0, le=100, example=90.9, title="average nucleotide identity (%)")
    af: Optional[float] = Field(None, ge=0, le=1, example=0.9, title="alignment fraction")
    data: Json = Field(..., description='additional data returned by the program')


class AniCreateJobResponse(BaseModel):
    jobId: str = Field(..., example='68cc9610', title='unique ID associated with this job')


class AniJobResultResponse(BaseModel):
    """Represents an ANI job request, this contains a list of results."""
    jobId: int = Field(..., example='1', title="unique ID associated with this job")
    query: List[str] = Field(..., example=['GCA_123456789.1'],
                             description='collection of GenBank/RefSeq query accession(s)')
    reference: List[str] = Field(..., example=['GCF_123456789.1'],
                                 description='collection of GenBank/RefSeq reference accession(s)')
    paramsFastAni: Optional[AniParametersFastAni] = Field(None, description='FastANI parameters to run the program')
    paramsSkani: Optional[AniParametersSkani] = Field(None, description='skani parameters to run the program')
    program: AniProgram = Field(..., description='program and version used')
    results: List[AniResult] = Field(..., description='list of results')


class AniJobResultResponseIndex(BaseModel):
    """Represents an ANI job request, this contains a list of results specific to the index page."""
    jobId: int = Field(..., example='1', title="unique ID associated with this job")
    query: List[AniGenomeValidationResponse] = Field(..., example=['GCA_123456789.1'],
                                                     description='collection of GenBank/RefSeq query accession(s)')
    reference: List[AniGenomeValidationResponse] = Field(..., example=['GCF_123456789.1'],
                                                         description='collection of GenBank/RefSeq reference accession(s)')
    paramsFastAni: Optional[AniParametersFastAni] = Field(None, description='FastANI parameters to run the program')
    paramsSkani: Optional[AniParametersSkani] = Field(None, description='skani parameters to run the program')
    program: AniProgram = Field(..., description='program and version used')


class UserGenomeDeleteAfterEnum(Enum):
    DISABLED = "disabled"
    HOUR_1 = "1_hour"
    DAY_1 = "1_day"
    WEEK_1 = "1_week"
    MONTH_1 = "1_month"



class AniUploadedGenomeRequest(BaseModel):
    """The request that encapsulates uploaded genome file."""
    deleteAfter: UserGenomeDeleteAfterEnum = Field(...)

class AniJobRequestDbModelUserFile(BaseModel):
    name: str = Field(...)
    md5: str = Field(...)

class AniJobResultDbModel(BaseModel):
    pass


class AniJobRequestDbModel(BaseModel):
    """The request payload stored in the database."""
    query: List[str] = Field(..., example=['GCA_123456789.1'],
                             description='collection of GenBank/RefSeq query accession(s)')
    reference: List[str] = Field(..., example=['GCF_123456789.1'],
                                 description='collection of GenBank/RefSeq reference accession(s)')
    paramsFastAni: Optional[AniParametersFastAni] = Field(None, description='FastANI parameters to run the program')
    paramsSkani: Optional[AniParametersSkani] = Field(None, description='skani parameters to run the program')
    userGenomes: List[AniJobRequestDbModelUserFile] = Field(...)
    program: AniProgram = Field(..., description='program and version requested')


class AniJobRequest(BaseModel):
    """The request body used to create an ANI job."""
    query: List[str] = Field(..., example=['GCA_123456789.1'],
                             description='collection of GenBank/RefSeq query accession(s)')
    reference: List[str] = Field(..., example=['GCF_123456789.1'],
                                 description='collection of GenBank/RefSeq reference accession(s)')
    params: Optional[AniParametersSkani] = Field(None, description='parameters to run the program')
    userGenomes: Optional[AniUploadedGenomeRequest] = Field(None)
    program: AniProgram = Field(..., description='program and version requested')
    email: Optional[str] = Field(None, example='foo@bar.com', title="e-mail address to be notified on completion")

    def validate_email(self):
        if self.email is not None and len(self.email) > 3:
            if not is_valid_email(self.email):
                raise HttpBadRequest('The e-mail address is invalid.')

    def validate_parameters(self):
        if self.paramsFastAni is not None and self.paramsSkani is not None:
            raise HttpBadRequest('Only one of the program parameters can be supplied.')
        if self.paramsFastAni is not None:
            self.paramsFastAni.sanitise_for_program(self.program)
            if self.paramsFastAni.all_params_null():
                self.paramsFastAni = None
        if self.paramsSkani is not None:
            self.paramsSkani.sanitise_for_program(self.program)
            if self.paramsSkani.all_params_null():
                self.paramsSkani = None
        return

    def validate_genomes(self):
        n_pairwise = len(set(self.query)) * len(set(self.reference))
        if n_pairwise > ANI_MAX_PAIRWISE:
            raise HttpBadRequest(f'Too many pairwise comparisons: {n_pairwise:,} > '
                                 f'{ANI_MAX_PAIRWISE:,}')
        if n_pairwise == 0:
            raise HttpBadRequest('No pairwise comparisons requested')


class AniTableResultStatus(Enum):
    RUNNING = "RUNNING",
    QUEUED = "QUEUED",
    ERROR = "ERROR"


class AniTableResultRow(BaseModel):
    """A row within the tabular results."""
    query: str = Field(...)
    reference: str = Field(...)
    ani: Optional[float] = Field(...)
    af: Optional[float] = Field(...)
    status: AniTableResultStatus = Field(...)

    fastAniMappedFrags: Optional[int] = Field(None)
    fastAniTotalFrags: Optional[int] = Field(None)

    skaniNumRefContigs: Optional[int] = Field(None)
    skaniNumQryContigs: Optional[int] = Field(None)
    skaniAni5Percentile: Optional[int] = Field(None)
    skaniAni95Percentile: Optional[int] = Field(None)
    skaniStdDev: Optional[int] = Field(None)
    skaniRef90CtgLen: Optional[int] = Field(None)
    skaniRef50CtgLen: Optional[int] = Field(None)
    skaniRef10CtgLen: Optional[int] = Field(None)
    skaniQry90CtgLen: Optional[int] = Field(None)
    skaniQry50CtgLen: Optional[int] = Field(None)
    skaniQry10CtgLen: Optional[int] = Field(None)
    skaniAvgChainLen: Optional[int] = Field(None)
    skaniTotalBasesCovered: Optional[int] = Field(None)


class AniTableResult(BaseModel):
    """The data returned when the result view is queried."""
    program: AniProgramEnum = Field(...)
    rows: List[AniTableResultRow] = Field(...)


class AniConfigResponse(BaseModel):
    """The configuration options available to the user."""
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
    supportedPrograms: List[AniProgram] = Field(
        list(ANI_PROGRAM_LIST),
        description='list of supported programs and versions'
    )
    maxQueuePendingJobs: int = Field(
        ANI_QUEUE_MAX_PENDING_JOBS,
        description='maximum number of pending jobs allowed in the queue'
    )





