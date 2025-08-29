from typing import List

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.db.models import Genome


def genomes_all(db: Session) -> List[str]:
    accessions = db.execute(sa.select([Genome.id_at_source]).order_by(Genome.id_at_source).distinct()).all()
    return [accession.id_at_source for accession in accessions]
