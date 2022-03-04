from typing import List

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from api.controller.genome import genome_metadata, genome_taxon_history, genome_card
from api.db import get_gtdb_db, get_gtdb_web_db
from api.model.genome import GenomeMetadata, GenomeTaxonHistory, GenomeCard

router = APIRouter(prefix='/genome', tags=['genome'])


@router.get('/{accession}/metadata', response_model=GenomeMetadata)
def v_get_genome_metadata(accession: str, db: Session = Depends(get_gtdb_db)):
    return genome_metadata(accession, db)


@router.get('/{accession}/taxon-history', response_model=List[GenomeTaxonHistory])
def v_get_genome_taxon_history(accession: str, db: Session = Depends(get_gtdb_web_db)):
    return genome_taxon_history(accession, db)


@router.get('/{accession}/card', response_model=GenomeCard,
            summary='Taxon metadata.')
async def v_genome_card(accession: str, db_gtdb: Session = Depends(get_gtdb_db),
                  db_web: Session = Depends(get_gtdb_web_db)):
    return genome_card(accession, db_gtdb, db_web)
