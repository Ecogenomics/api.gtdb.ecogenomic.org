from fastapi import APIRouter
from fastapi.responses import Response

from api.controller.status import get_status
from api.db import GtdbWebDbDep
from api.model.status import StatusDbResponse

router = APIRouter(prefix='/status', tags=['status'])


@router.get(
    '/db',
    summary='Return the database status.',
    response_model=StatusDbResponse
)
def v_get_status(response: Response, db: GtdbWebDbDep):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return get_status(db)
