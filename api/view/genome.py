from typing import List, Annotated

from fastapi import APIRouter, Path

from api.controller.genome import genome_metadata, genome_taxon_history, genome_card
from api.db import GtdbDbDep, GtdbWebDbDep
from api.model.genome import GenomeMetadata, GenomeTaxonHistory, GenomeCard

router = APIRouter(prefix='/genome', tags=['genome'])


@router.get(
    '/{accession}/metadata',
    response_model=GenomeMetadata,
    summary='Return minimal metadata about a specific genome, namely if it is listed as a surveillance genome within NCBI.'
)
def v_get_genome_metadata(
        accession: Annotated[str, Path(
            ...,
            description='The NCBI accession to search.',
            example='GCA_123456789.1',
        )],
        db: GtdbDbDep
):
    return genome_metadata(accession, db)


@router.get(
    '/{accession}/taxon-history',
    response_model=List[GenomeTaxonHistory],
    summary='Return the taxonomic history of a specific genome across GTDB releases.'
)
def v_get_genome_taxon_history(
        accession: Annotated[str, Path(
            description='The NCBI/GTDB accession to search.',
            openapi_examples={
                "simple": {
                    "summary": "Short accession",
                    "value": "G005435135",
                },
                "gcf": {
                    "summary": "GCF short",
                    "value": "GCF_005435135.1",
                },
                "gcf_assembly": {
                    "summary": "GCF long Assembly",
                    "value": "GCF_005435135.1_ASM543513v1_genomic",
                },
                "rs_long": {"summary": "RefSeq long", "value": "RS_GCF_005435135.1"},
                "gb_long": {"summary": "GenBank long", "value": "GB_GCA_005435135.1"},
            },
        )],
        db: GtdbWebDbDep
):
    return genome_taxon_history(accession, db)


@router.get(
    '/{accession}/card',
    response_model=GenomeCard,
    summary='Return mostly all metadata associated with a genome for display on the genome page.'
)
def v_genome_card(
        accession: Annotated[str, Path(
            ...,
            description='The NCBI accession to search.',
            example='GCA_123456789.1',
        )],
        db_gtdb: GtdbDbDep,
        db_web: GtdbWebDbDep):
    return genome_card(accession, db_gtdb, db_web)
