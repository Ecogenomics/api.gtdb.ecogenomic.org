import sqlmodel as sm
from sqlmodel import Session

from api.db.gtdb_web import DbGtdbTree
from api.model.taxa import TaxaAll


def get_all_taxa(db: Session) -> TaxaAll:
    # Get parent info
    query = (
        sm.select(DbGtdbTree.taxon)
        .where(DbGtdbTree.type != 'genome')
        .where(DbGtdbTree.taxon != 'root')
        .distinct()
    )
    results = db.exec(query).all()
    return TaxaAll(taxa=sorted(results))
