from fastapi import APIRouter

from api.controller.taxa import get_all_taxa
from api.db import GtdbWebDbDep
from api.model.taxa import TaxaAll

router = APIRouter(prefix='/taxa', tags=['taxa'])


@router.get(
    '/all',
    response_model=TaxaAll,
    summary='Return all taxa in the GTDB.'
)
def v_get_all_taxa(db: GtdbWebDbDep):
    return get_all_taxa(db)
