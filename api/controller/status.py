from time import time

from sqlalchemy import sql
from sqlalchemy.orm import Session

from api.model.status import StatusDbResponse


def get_status(db: Session) -> StatusDbResponse:
    start = time()
    try:
        results = db.execute(sql.text("""SELECT True AS is_ok;"""))
        rows = [x.is_ok for x in results]
        is_ok = len(rows) == 1 and rows[0] is True
    except Exception:
        is_ok = False
    end = time()
    return StatusDbResponse(timeMs=round((end - start) * 1000, 4), online=is_ok)
