#  Copyright 2026 Collate
#  Licensed under the Collate Community License, Version 1.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  https://github.com/open-metadata/OpenMetadata/blob/main/ingestion/LICENSE
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
SQLAlchemy dialect for Dremio, on top of `sqlalchemy-dremio` (Arrow Flight).

`sqlalchemy-dremio` targets SQLAlchemy 1.x: its reflection methods run plain
strings with `connection.execute(...)`, which SQLAlchemy 2 rejects. The
dialect below keeps its Arrow Flight transport and replaces the reflection
methods the connector relies on, reading the catalog from `INFORMATION_SCHEMA`.

The driver drops the parameters it is given, so values are written in the SQL
text, escaped, and statements go through `exec_driver_sql` so that SQLAlchemy
does not read a `:` in a name as a bind parameter.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import types
from sqlalchemy.dialects import registry
from sqlalchemy.engine import Connection
from sqlalchemy_dremio import query as driver_query
from sqlalchemy_dremio.flight import DremioCompiler, DremioDialect_flight

DREMIO_DIALECT_NAME = "dremio.flight"

GET_SCHEMA_NAMES = "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA"

GET_TABLE_NAMES = 'SELECT TABLE_NAME FROM INFORMATION_SCHEMA."TABLES" WHERE TABLE_SCHEMA = {schema}'

GET_TABLE_EXISTS = (
    'SELECT COUNT(*) FROM INFORMATION_SCHEMA."TABLES" WHERE TABLE_SCHEMA = {schema} AND TABLE_NAME = {table}'
)

# INFORMATION_SCHEMA."COLUMNS" is filled lazily for lakehouse tables (Iceberg,
# Delta...): it stays empty until Dremio has read the table once. DESCRIBE
# loads the schema on demand, so it is what the columns are read from.
DESCRIBE_TABLE = "DESCRIBE {path}"

GET_VIEW_DEFINITION = (
    'SELECT VIEW_DEFINITION FROM INFORMATION_SCHEMA."VIEWS" WHERE TABLE_SCHEMA = {schema} AND TABLE_NAME = {view}'
)

# Types Dremio reports in INFORMATION_SCHEMA.COLUMNS.DATA_TYPE
SIMPLE_TYPES = {
    "BOOLEAN": types.BOOLEAN,
    "TINYINT": types.SMALLINT,
    "SMALLINT": types.SMALLINT,
    "INTEGER": types.INTEGER,
    "BIGINT": types.BIGINT,
    "FLOAT": types.FLOAT,
    "DOUBLE": types.DOUBLE,
    "DATE": types.DATE,
    "TIME": types.TIME,
    "TIMESTAMP": types.TIMESTAMP,
    "BINARY VARYING": types.VARBINARY,
}


# The driver converts the columns of a result by the name of their pandas type,
# and only knows datetime64[ns]. Dremio timestamps have a precision of a
# millisecond, which pandas 2 keeps as datetime64[ms].
RESULT_TYPES = {
    "datetime64[s]": types.DATETIME,
    "datetime64[ms]": types.DATETIME,
    "datetime64[us]": types.DATETIME,
    "int8": types.SMALLINT,
    "int16": types.SMALLINT,
}

for pandas_type, sql_type in RESULT_TYPES.items():
    driver_query._type_map.setdefault(pandas_type, sql_type)


def literal(value: str) -> str:
    """Write `value` as a single quoted SQL string"""
    return "'" + str(value).replace("'", "''") + "'"


def quote_path(schema: Optional[str], table: str) -> str:
    """
    Write the path of a table, where `schema` is the dotted path of its space
    and folders (e.g. `space.folder`): every part is a quoted identifier.
    """
    parts = [*(schema.split(".") if schema else []), table]
    return ".".join('"' + part.replace('"', '""') + '"' for part in parts)


def get_column_type(
    data_type: str,
    length: Optional[int],
    precision: Optional[int],
    scale: Optional[int],
) -> types.TypeEngine:
    """Translate a Dremio data type into a SQLAlchemy type"""
    data_type = (data_type or "").upper()

    if data_type in ("CHARACTER VARYING", "CHARACTER", "VARCHAR"):
        return types.VARCHAR(length) if length else types.VARCHAR()
    if data_type in ("DECIMAL", "NUMERIC"):
        # Dremio reports precision and scale as floats (e.g. 38.0)
        return types.DECIMAL(int(precision), int(scale or 0)) if precision else types.DECIMAL()
    if data_type in SIMPLE_TYPES:
        return SIMPLE_TYPES[data_type]()
    if data_type.startswith("INTERVAL"):
        return types.Interval()

    # ROW, LIST, MAP... are not reflected with their inner fields here
    return types.NullType()


class DremioStatementCompiler(DremioCompiler):
    """
    The driver drops the parameters of a statement, so they are written in it
    """

    def visit_bindparam(self, bindparam, **kw):
        kw["literal_binds"] = True
        return super().visit_bindparam(bindparam, **kw)


class DremioFlightDialect(DremioDialect_flight):
    """
    `dremio+flight` dialect whose reflection works with SQLAlchemy 2
    """

    # The driver names its dialect "dremio+flight". The name is the one the
    # profiler rules are registered for, see Dialects.Dremio.
    name = "dremio"
    driver = "flight"

    statement_compiler = DremioStatementCompiler

    def get_schema_names(self, connection: Connection, schema: Optional[str] = None, **kw) -> List[str]:
        return [row[0] for row in connection.exec_driver_sql(GET_SCHEMA_NAMES)]

    def get_table_names(self, connection: Connection, schema: Optional[str] = None, **kw) -> List[str]:
        query = GET_TABLE_NAMES.format(schema=literal(schema or ""))
        return [row[0] for row in connection.exec_driver_sql(query)]

    def has_table(
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> bool:
        query = GET_TABLE_EXISTS.format(schema=literal(schema or ""), table=literal(table_name))
        return connection.exec_driver_sql(query).scalar() > 0

    def get_columns(
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> List[Dict[str, Any]]:
        query = DESCRIBE_TABLE.format(path=quote_path(schema, table_name))
        return [
            {
                "name": name,
                "type": get_column_type(data_type, None, precision, scale),
                "nullable": is_nullable != "NO",
                "default": None,
                "comment": None,
            }
            for name, data_type, is_nullable, precision, scale in (
                row[:5] for row in connection.exec_driver_sql(query)
            )
        ]

    def get_view_definition(
        self,
        connection: Connection,
        view_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> Optional[str]:
        query = GET_VIEW_DEFINITION.format(schema=literal(schema or ""), view=literal(view_name))
        return connection.exec_driver_sql(query).scalar()


# Replaces the entry point of `sqlalchemy-dremio` for `dremio+flight`
registry.register(DREMIO_DIALECT_NAME, __name__, DremioFlightDialect.__name__)
