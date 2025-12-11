from time import time

import sqlmodel as sm
from sqlmodel import Session

from api.model.status import StatusDbResponse


def get_status(db: Session) -> StatusDbResponse:
    start = time()
    try:
        results = db.exec(sm.text("""SELECT True AS is_ok;""")).first()
        is_ok = results.is_ok
    except Exception:
        is_ok = False
    end = time()
    return StatusDbResponse(timeMs=round((end - start) * 1000, 4), online=is_ok)
