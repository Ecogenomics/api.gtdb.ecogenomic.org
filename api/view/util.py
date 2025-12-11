from typing import Optional

from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import StreamingResponse

from api.controller.util import send_contact_us_email, convert_tree_accessions
from api.db import GtdbWebDbDep, GtdbDbDep
from api.model.util import UtilContactEmailRequest, PrevUserEnum, NoUserAccEnum, UserOnlyEnum

router = APIRouter(prefix='/util', tags=['util'])


@router.post(
    '/contact',
    summary='Send a contact us e-mail.',
    include_in_schema=False
)
async def v_util_post_contact(request: UtilContactEmailRequest):
    return await send_contact_us_email(request)


@router.post(
    "/convert-tree-accessions",
    response_class=StreamingResponse,
    include_in_schema=False
)
def v_convert_tree_accessions(
        db_web: GtdbWebDbDep,
        db_gtdb: GtdbDbDep,
        noUserAcc: NoUserAccEnum = Form(...),
        prevUser: PrevUserEnum = Form(...),
        userOnly: UserOnlyEnum = Form(...),
        newickFile: Optional[UploadFile] = None,
        newickString: Optional[str] = Form(None)
):
    data = convert_tree_accessions(db_web, db_gtdb, noUserAcc, prevUser, userOnly, newickFile, newickString)
    response = StreamingResponse(data, media_type='application/zip')
    response.headers["Content-Disposition"] = f"attachment; filename=gtdb-convert-accessions.zip"
    response.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    return response
