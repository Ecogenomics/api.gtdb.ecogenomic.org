import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.db.models import DbGtdbTree
from api.model.taxa import TaxaAll


def get_all_taxa(db: Session) -> TaxaAll:
    # Get parent info
    query = sa.select([DbGtdbTree.taxon]).where(DbGtdbTree.type != 'genome')
    results = db.execute(query).fetchall()
    results = sorted({x.taxon for x in results} - {'root'})
    return TaxaAll(taxa=results)
