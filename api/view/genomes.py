from typing import List

from fastapi import APIRouter

from api.controller.genomes import genomes_all
from api.db import GtdbDbDep

router = APIRouter(prefix='/genomes', tags=['genomes'])


@router.get(
    '/all', response_model=List[str], summary='Return a list of all GTDB genomes')
def v_get_genomes_all(db: GtdbDbDep):
    return genomes_all(db)
