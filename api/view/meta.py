from fastapi import APIRouter
from fastapi.responses import Response

from api.controller.meta import get_meta_version
from api.model.meta import MetaVersionResponse

router = APIRouter(prefix='/meta', tags=['meta'])


@router.get('/version', summary='Return the API version.', response_model=MetaVersionResponse)
async def v_meta_version(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return get_meta_version()
