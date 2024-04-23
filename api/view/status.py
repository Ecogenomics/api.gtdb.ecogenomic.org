from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.controller.status import get_status
from api.db import get_gtdb_web_db
from api.model.status import StatusDbResponse

router = APIRouter(prefix='/status', tags=['status'])


@router.get('/db', summary='Return the database status.', response_model=StatusDbResponse)
def v_get_status(response: Response, db: Session = Depends(get_gtdb_web_db)):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return get_status(db)
