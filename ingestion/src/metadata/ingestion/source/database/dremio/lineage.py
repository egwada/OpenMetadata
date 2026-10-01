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
Dremio lineage module
"""

from collections.abc import Iterable

import sqlglot
from sqlglot import exp

from metadata.ingestion.source.database.dremio.queries import DREMIO_SQL_STATEMENT
from metadata.ingestion.source.database.dremio.query_parser import DremioQueryParserSource
from metadata.ingestion.source.database.lineage_source import LineageSource
from metadata.ingestion.source.models import TableView
from metadata.utils.logger import ingestion_logger

logger = ingestion_logger()

SQLGLOT_DIALECT = "dremio"


def qualify_namespace_paths(sql: str) -> str:
    """
    Spell out the tables that a view reads at the root of a namespace.

    A Dremio path is absolute: `finance.revenue_by_country` is the object
    `revenue_by_country` of the space `finance`. OpenMetadata names such an
    object `<service>.finance.finance.revenue_by_country`: the namespace is the
    database and, as it has no folder, the schema too. Left as it is, the
    two-part name is looked up in the database of the view that reads it, and
    the lineage of a view built on a view of another space is lost.
    """
    try:
        tree = sqlglot.parse_one(sql, dialect=SQLGLOT_DIALECT)
    except sqlglot.errors.SqlglotError:
        logger.debug("The view definition is not parsed by sqlglot, it is left as it is")
        return sql
    for table in tree.find_all(exp.Table):
        if table.db and not table.catalog:
            table.set("catalog", table.args["db"].copy())
    return tree.sql(dialect=SQLGLOT_DIALECT)


class DremioLineageSource(DremioQueryParserSource, LineageSource):
    """
    Dremio class for Lineage

    The lineage of a view, at table and column level, comes from the SQL of the
    view stored by the metadata workflow, which the parser of the parent class
    reads. The lineage of the tables that queries fill comes from the job
    history, limited to the statements that write.
    """

    sql_stmt = DREMIO_SQL_STATEMENT

    def view_lineage_producer(self) -> Iterable[TableView]:
        for view in super().view_lineage_producer():
            if not view.view_definition:
                yield view
                continue
            yield view.model_copy(update={"view_definition": qualify_namespace_paths(view.view_definition)})

    filters = """
        AND (
            lower("query") LIKE '%%create%%table%%as%%'
            OR lower("query") LIKE '%%insert%%into%%'
            OR lower("query") LIKE '%%merge%%into%%'
        )
    """
