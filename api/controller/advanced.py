import re
from typing import Dict, Any

import sqlmodel as sm
from sqlmodel import Session

from api.exceptions import HttpBadRequest
from api.model.advanced import (
    AdvancedSearchOptionsResponse,
    AdvancedSearchOperator,
    AdvancedSearchDataTypeResponse,
    AdvancedDataType,
    AdvancedSearchOperatorResponse,
    AdvancedSearchColumn,
    AdvancedSearchColumnResponse,
    AdvancedSearchOption,
    AdvancedSearchResult,
    AdvancedSearchHeader
)
from api.util.url import base64url_to_str

# Pre-compiled Regex
RE_GROUPS = re.compile(r'^(\d+)~(\d+)~?(.+)?$')
RE_DIGIT = re.compile(r'(\d+)')

# Configuration
BASE_COLS = (
    AdvancedSearchColumn.ACCESSION,
    AdvancedSearchColumn.ORGANISM_NAME,
    AdvancedSearchColumn.NCBI_TAXONOMY,
    AdvancedSearchColumn.GTDB_TAXONOMY,
    AdvancedSearchColumn.GTDB_REP_OF_SPECIES,
    AdvancedSearchColumn.GTDB_TYPE_MAT
)


def get_advanced_search_options() -> list[AdvancedSearchOptionsResponse]:
    out = list()
    for operator in AdvancedSearchOption:
        out.append(AdvancedSearchOptionsResponse(id=operator.id, display=operator.display))
    return out


def get_advanced_search_data_types() -> list[AdvancedSearchDataTypeResponse]:
    out = list()
    for dt in AdvancedDataType:
        out.append(AdvancedSearchDataTypeResponse(name=dt.name, value=dt.value))
    return out


def get_advanced_search_operators() -> list[AdvancedSearchOperatorResponse]:
    out = list()
    for op in AdvancedSearchOperator:
        out.append(AdvancedSearchOperatorResponse(id=op.id, display=op.display, dataType=op.dt.value))
    return out


def get_advanced_search_columns() -> list[AdvancedSearchColumnResponse]:
    out = list()
    for col in AdvancedSearchColumn:
        if col.options:
            cur_option = [AdvancedSearchOptionsResponse(id=x.id, display=x.display)
                          for x in col.options]
        else:
            cur_option = None
        out.append(AdvancedSearchColumnResponse(
            id=col.id,
            display=col.display,
            dataType=col.dt.value,
            options=cur_option,
            group=col.group
        ))
    return out


# helper functions
def parse_groups(groups: Dict[int, str]) -> dict[int, tuple[AdvancedSearchColumn, AdvancedSearchOperator, str]]:
    out = dict()
    for i, group in groups.items():
        re_hits = RE_GROUPS.search(group)
        cur_col_id = int(re_hits.group(1))
        cur_op_id = int(re_hits.group(2))
        cur_col = [x for x in AdvancedSearchColumn if x.id == cur_col_id][0]
        cur_op = [x for x in AdvancedSearchOperator if x.id == cur_op_id][0]
        if cur_col.dt != cur_op.dt:
            raise ValueError('Search operator does not match column.')
        out[i] = (cur_col, cur_op, re_hits.group(3))
    return out


def get_method(
        expression,
        groups: dict[int, tuple[AdvancedSearchColumn, AdvancedSearchOperator, str]],
        db: Session
):
    mv_prefix = 'mv'

    # Set the operators
    expression = expression.replace('&', ' AND ').replace('|', ' OR ')

    # Create the where clause
    new_groups = dict()
    parameters = dict()
    for i, (column, operator, value) in groups.items():

        # Only boolean data types have a different syntax.
        if operator.dt == AdvancedDataType.BOOLEAN:
            cur_exp = f'{mv_prefix}.{column.column.key} IS {operator.operator}'

        # Enum types can have null values
        elif operator.dt == AdvancedDataType.ENUM:
            cur_operator = operator.operator
            cur_arg = f'a{i}'
            parameters[cur_arg] = [x for x in column.options if x.id == int(value)][0].keyword
            if parameters[cur_arg] is None:
                if cur_operator == '=':
                    cur_operator = 'IS'
                else:
                    cur_operator = 'IS NOT'
            cur_exp = f'{mv_prefix}.{column.column.key} {cur_operator} :{cur_arg}'

        # Everything else
        else:
            cur_operator = operator.operator
            if operator.operator in {'ILIKE', 'LIKE'}:
                cur_value = f'%{value}%'
            else:
                cur_value = value
            cur_arg = f'a{i}'
            parameters[cur_arg] = cur_value
            cur_exp = f'{mv_prefix}.{column.column.key} {cur_operator} :{cur_arg}'
        new_groups[i] = cur_exp

    # Replace the groups at once, otherwise values that contain ints could override.
    list_query = list()
    previous_idx = 0
    for hit in RE_DIGIT.finditer(expression):
        idx_from, idx_to = hit.span()
        cur_val = int(hit.group())
        list_query.append(expression[previous_idx:idx_from])
        list_query.append(new_groups[cur_val])
        previous_idx = idx_to
    list_query.append(expression[previous_idx:])
    str_where = ''.join(list_query)

    # Build the query
    set_base_cols = frozenset(BASE_COLS)
    columns_to_select = list(BASE_COLS)
    columns_to_select.extend([v[0] for k, v in groups.items() if v[0] not in set_base_cols])
    str_columns = ', '.join([f'mv.{x.column.key}' for x in columns_to_select])
    query = sm.text(f"SELECT {str_columns} FROM genomes g INNER JOIN metadata_mtview mv "
                    f"on mv.id = g.id WHERE g.genome_source_id != 1 AND ({str_where}) "
                    f"ORDER BY g.id")
    results = db.exec(query, params=parameters).all()
    out_rows = [x._asdict() for x in results]
    out_headers = [AdvancedSearchHeader(text=x.display, value=x.column.key) for x in columns_to_select]
    return AdvancedSearchResult(headers=out_headers, rows=out_rows)


def get_advanced_search(query: Dict[str, Any], db: Session) -> AdvancedSearchResult:
    """This method expects all parameters to be URL-Safe Base64 encoded.
         i.e. the static/js/util.js "base64EncodeUrl" method.

         The "exp" argument contains the logic, with & = AND, and | = OR.
         For example, three arguments may look like this:
             raw:    exp=(0&1)|2
             base64: exp=KDAmMSl8Mg~~

         There will then need to be n arguments that contain the column information
         for each of the integers in the logic above. These arguments will
         encode the column, and operation type (e.g. accession = "asd"). The integers
         that encode the columns, and operators are encoded in SearchColumn, and
         SearchOperator respectively (~ will separate each encoding integer).
         The format will be <argument_id>=<column_id>~<operation_id>~<value>
             logic: Argument 0 will search GTDB taxonomy contains "asd".
                    GTDB_TAXONOMY is SearchColumn.GTDB_TAXONOMY.value = 1
                    STR_CONTAINS is SearchOperator.STR_CONTAINS.value = 2
             raw:    0=1~2~asd
             base64: MX4yfmFzZA~~

         The final URL will then be:
             /api/v2/search/advanced?exp=KDAmMSl8Mg~~&=0MX4yfmFzZA~~&1=...&2=...
    """

    # Get and validate the expression
    expression = query.get('exp')
    if expression is None:
        raise HttpBadRequest('You must supply a search expression.')
    expression = base64url_to_str(expression)

    # Get and validate the groups
    groups = RE_DIGIT.findall(expression)
    if not groups or len(groups) == 0:
        raise HttpBadRequest('No search groups detected.')
    try:
        int_groups = tuple([int(x) for x in groups])
    except ValueError:
        raise HttpBadRequest('Could not convert group to an integer.')

    int_groups_set = frozenset(int_groups)
    if len(int_groups_set) != len(int_groups):
        raise HttpBadRequest('Duplicate group number used.')

    expr_groups = {i: query.get(str(i)) for i in int_groups}
    if not all(expr_groups.values()):
        raise HttpBadRequest('Not all groups have an expression associated with them.')
    expr_groups = {i: base64url_to_str(x) for i, x in expr_groups.items()}

    try:
        parsed_groups = parse_groups(expr_groups)
    except Exception:
        raise HttpBadRequest('Error parsing groups.')

    return get_method(expression, parsed_groups, db=db)


def adv_search_query_to_rows(result: AdvancedSearchResult):
    out = list()

    header_row = list()
    for header in result.headers:
        header_row.append(header.text)
    out.append(header_row)

    for row in result.rows:
        row_out = list()
        for key in result.headers:
            row_out.append(row[key.value])
        out.append(row_out)

    return out
