from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from api.controller.taxa import get_all_taxa
from api.db import get_gtdb_web_db
from api.model.taxa import TaxaAll

router = APIRouter(prefix='/taxa', tags=['taxa'])


@router.get('/all', response_model=TaxaAll,
            summary='Return all taxa in the GTDB.')
def v_get_all_taxa(db: Session = Depends(get_gtdb_web_db)):
    return get_all_taxa(db)
