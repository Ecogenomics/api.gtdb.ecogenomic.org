from typing import List

from pydantic import BaseModel, Field


class AreGenomesDownloadedRequest(BaseModel):
    genomes: List[str] = Field(..., description='List of genome accessions to check',
                               example=['GCA_000001405.1', 'GCF_123456789.1'])


class AreGenomesDownloadedItem(BaseModel):
    gid: str = Field(..., description='Genome accession', example='GCA_000001405.1')
    downloaded: bool = Field(..., description='Whether the genome is downloaded', example=True)


class AreGenomesDownloadedResponse(BaseModel):
    genomes: List[AreGenomesDownloadedItem] = Field(..., description='List of genome accessions checked')
