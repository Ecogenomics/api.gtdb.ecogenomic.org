from typing import List

import sqlmodel as sm
from sqlmodel import Session

from api.db.gtdb import DbGenomes


def genomes_all(db: Session) -> List[str]:
    accessions = db.exec(sm.select(DbGenomes.id_at_source).order_by(DbGenomes.id_at_source).distinct()).all()
    out = list()
    out.extend(accessions)
    return out

