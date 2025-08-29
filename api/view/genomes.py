from typing import List

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from api.controller.genomes import genomes_all
from api.db import get_gtdb_db

router = APIRouter(prefix='/genomes', tags=['genomes'])


@router.get('/all', response_model=List[str], summary='Return a list of all GTDB genomes')
def v_genomes_all(db: Session = Depends(get_gtdb_db)):
    return genomes_all(db)
