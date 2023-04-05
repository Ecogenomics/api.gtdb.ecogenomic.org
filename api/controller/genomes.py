from typing import List

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.db.models import Genome, GtdbCommonGenomes
from api.model.genomes import AreGenomesDownloadedRequest, AreGenomesDownloadedResponse, AreGenomesDownloadedItem


def genomes_all(db: Session) -> List[str]:
    accessions = db.execute(sa.select([Genome.id_at_source]).order_by(Genome.id_at_source).distinct()).all()
    return [accession.id_at_source for accession in accessions]

def are_genomes_downloaded(request: AreGenomesDownloadedRequest, db: Session) -> AreGenomesDownloadedResponse:

    # Deduplicate the list of genomes
    genomes = set(request.genomes)

    # Run the query
    query = sa.select([GtdbCommonGenomes.name]).where(GtdbCommonGenomes.name.in_(genomes))
    results = db.execute(query).fetchall()

    item = AreGenomesDownloadedItem(gid='asd', downloaded=True)
    return AreGenomesDownloadedResponse(genomes=[item])
