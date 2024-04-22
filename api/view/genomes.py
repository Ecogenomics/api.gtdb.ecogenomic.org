from typing import List

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from api.controller.genomes import genomes_all, are_genomes_downloaded
from api.db import get_gtdb_db, get_gtdb_common_db
from api.model.genomes import AreGenomesDownloadedRequest, AreGenomesDownloadedResponse

router = APIRouter(prefix='/genomes', tags=['genomes'])


@router.get('/all', response_model=List[str], summary='Return a list of all GTDB genomes')
def v_genomes_all(db: Session = Depends(get_gtdb_db)):
    return genomes_all(db)

# @router.post('/are-downloaded', response_model=AreGenomesDownloadedResponse, summary='Check if a list of genomes are downloaded')
# def v_genomes_are_downloaded(request: AreGenomesDownloadedRequest, db: Session = Depends(get_gtdb_common_db)):
#     return are_genomes_downloaded(request, db)
