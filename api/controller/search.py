import re
import shlex
from typing import List

import sqlalchemy as sa
from sqlalchemy.orm import Session

from api.db.models import GtdbSearchMtView
from api.exceptions import HttpBadRequest
from api.model.search import SearchGtdbRequest, SearchGtdbResponse, SearchColumnEnum, SearchGtdbRow
from api.util.accession import canonical_gid


def generate_search_query_2(list_fields, list_keywords):
    where = list()
    for field in list_fields:
        where.extend([field.ilike(f'%{x}%') for x in list_keywords])
    return where


def search_gtdb_to_rows(response: SearchGtdbResponse) -> List:
    out = list()
    out.append([
        'accession',
        'ncbi_organism_name',
        'ncbi_taxonomy',
        'gtdb_taxonomy',
        'gtdb_species_representative',
        'ncbi_type_material'
    ])
    for row in response.rows:
        out.append([
            row.accession,
            row.ncbiOrgName,
            row.ncbiTaxonomy,
            row.gtdbTaxonomy,
            row.isGtdbSpeciesRep,
            row.isNcbiTypeMaterial
        ])
    return out


def search_gtdb(request: SearchGtdbRequest, db: Session) -> SearchGtdbResponse:
    # If the search string matches an accession, convert it to the canonical gid
    keywrd = request.search.strip()
    if re.match(r'^(?:GB_|RS_)?(?:GCA|GCF)+_\d{9}\.\d$', keywrd):
        keywrd = canonical_gid(keywrd)

    try:
        # Don't split if a group is surrounded in parenthesis
        keywords = [x for x in shlex.split(keywrd) if len(x) > 0]
    except ValueError:
        # Unclosed parenthesis
        keywords = [x for x in keywrd.split(' ') if len(x) > 0]

    if request.searchField is SearchColumnEnum.ALL:
        list_fields = (GtdbSearchMtView.gtdb_taxonomy,
                       GtdbSearchMtView.id_at_source,
                       GtdbSearchMtView.ncbi_organism_name,
                       GtdbSearchMtView.ncbi_taxonomy,
                       GtdbSearchMtView.ncbi_genbank_assembly_accession,
                       GtdbSearchMtView.formatted_source_id)
    elif request.searchField is SearchColumnEnum.NCBI_GENOME_ID and len(keywrd) > 1:
        list_fields = (GtdbSearchMtView.id_at_source,
                       GtdbSearchMtView.ncbi_genbank_assembly_accession,
                       GtdbSearchMtView.formatted_source_id)
    elif request.searchField is SearchColumnEnum.NCBI_ORG_NAME and len(keywrd) > 1:
        list_fields = [GtdbSearchMtView.ncbi_organism_name]
    elif request.searchField is SearchColumnEnum.NCBI_TAX and len(keywrd) > 1:
        list_fields = [GtdbSearchMtView.ncbi_taxonomy]
    elif request.searchField is SearchColumnEnum.GTDB_TAX and len(keywrd) > 1:
        list_fields = [GtdbSearchMtView.gtdb_taxonomy]
    else:
        raise HttpBadRequest(f"Method must be one of: {list(SearchColumnEnum)}")

    where_clause = generate_search_query_2(list_fields, keywords)

    query = (
        sa.select([GtdbSearchMtView.id_at_source,
                   GtdbSearchMtView.ncbi_organism_name,
                   GtdbSearchMtView.ncbi_taxonomy,
                   GtdbSearchMtView.gtdb_taxonomy,
                   GtdbSearchMtView.ncbi_genbank_assembly_accession,
                   GtdbSearchMtView.ncbi_type_material_designation,
                   GtdbSearchMtView.gtdb_representative]).
        where(sa.or_(*where_clause))
    )

    # Filters
    if request.ncbiTypeMaterialOnly:
        query = query.where(GtdbSearchMtView.ncbi_type_material_designation != None)
    if request.gtdbSpeciesRepOnly:
        query = query.where(GtdbSearchMtView.gtdb_representative == True)

    # Text filtering
    if request.filterText:
        query = query.where(sa.or_(
            GtdbSearchMtView.id_at_source.ilike(f'%{request.filterText}%'),
            GtdbSearchMtView.ncbi_organism_name.ilike(f'%{request.filterText}%'),
            GtdbSearchMtView.ncbi_taxonomy.ilike(f'%{request.filterText}%'),
            GtdbSearchMtView.gtdb_taxonomy.ilike(f'%{request.filterText}%'),
        ))

    # Determine the order_by clause
    if request.sortBy:
        order_by = list()
        for i, sort_by in enumerate(request.sortBy):
            # Attempt to get the sorting value, default to asc if not present
            try:
                sort_desc = request.sortDesc[i]
            except IndexError:
                sort_desc = False

            # Match the column
            if sort_by == 'accession':
                order_by.append(GtdbSearchMtView.id_at_source.desc() if sort_desc else GtdbSearchMtView.id_at_source)
            elif sort_by == 'ncbiOrgName':
                order_by.append(
                    GtdbSearchMtView.ncbi_organism_name.desc() if sort_desc else GtdbSearchMtView.ncbi_organism_name)
            elif sort_by == 'ncbiTaxonomy':
                order_by.append(GtdbSearchMtView.ncbi_taxonomy.desc() if sort_desc else GtdbSearchMtView.ncbi_taxonomy)
            elif sort_by == 'gtdbTaxonomy':
                order_by.append(GtdbSearchMtView.gtdb_taxonomy.desc() if sort_desc else GtdbSearchMtView.gtdb_taxonomy)
            elif sort_by == 'isGtdbSpeciesRep':
                order_by.append(
                    GtdbSearchMtView.gtdb_representative.desc() if sort_desc else GtdbSearchMtView.gtdb_representative)
            elif sort_by == 'isNcbiTypeMaterial':
                order_by.append(
                    GtdbSearchMtView.ncbi_type_material_designation.desc() if sort_desc else GtdbSearchMtView.ncbi_type_material_designation)
            else:
                raise HttpBadRequest(f'Unknown sortBy: {sort_by}')
        query = query.order_by(*order_by)

    # Get the total number of rows in the table before pagination
    total_rows = db.execute(sa.select(sa.func.count()).select_from(query)).scalar()

    # Add pagination
    if request.itemsPerPage and request.page:
        query = query.limit(request.itemsPerPage)
        query = query.offset(request.itemsPerPage * (request.page - 1))

    # Execute the query
    search_results = db.execute(query)
    all_rows = list()
    all_rows.extend(list(search_results))

    # if the genome is a surveillance genome, we need to check in a separate table
    # out_survey = None
    # if True or len(all_rows) == 0 and request.searchField in {SearchColumnEnum.NCBI_GENOME_ID, SearchColumnEnum.ALL}:
    #     survey_query = sa.select([SurveyGenomes.canonical_gid]).where(SurveyGenomes.canonical_gid == request.search)
    #     survey_hits = db.execute(survey_query)
    #     if len(list(survey_hits)) > 0:
    #         out_survey = request.search  # TODO: ??

    ncbi_type_material_categories = frozenset({
        'assembly from type material',
        'assembly designated as neotype',
        'assembly designated as reftype',
        'assembly designated as neotype',
    })

    # Apply filters and create objects
    out_rows = list()
    for hit in all_rows:
        out_rows.append(
            SearchGtdbRow(
                gid=hit.id_at_source,
                accession=hit.id_at_source,
                ncbiOrgName=hit.ncbi_organism_name,
                ncbiTaxonomy=hit.ncbi_taxonomy,
                gtdbTaxonomy=hit.gtdb_taxonomy,
                isGtdbSpeciesRep=hit.gtdb_representative is True,
                isNcbiTypeMaterial=hit.ncbi_type_material_designation in ncbi_type_material_categories
            )
        )

    return SearchGtdbResponse(rows=out_rows, totalRows=total_rows)
