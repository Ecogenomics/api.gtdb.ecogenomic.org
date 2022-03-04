from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.controller.species import get_species_cluster, util_species_all
from api.db import get_gtdb_db
from api.model.species import SpeciesCluster

router = APIRouter(prefix='/species', tags=['species'])


@router.get('/all', response_model=List[str],
            summary='Returns a list of all species clusters.')
def v_species_all(db: Session = Depends(get_gtdb_db)):
    return util_species_all(db)


@router.get('/search/{species}', response_model=SpeciesCluster,
            summary='Return information about a species.')
def species_cluster(species: str, db: Session = Depends(get_gtdb_db)):
    return get_species_cluster(species, db)

# @router.get('/heatmap/{species}', response_model=SpeciesHeatmap,
#             summary='Return data to generate the species heatmap.')
# def v_species_heatmap(species: str, db_web: Session = Depends(get_gtdb_web_db),
#                       db_gtdb: Session=Depends(get_gtdb_db)):
#     return c_species_heatmap(species, db_web, db_gtdb)
