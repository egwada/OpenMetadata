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

from metadata.ingestion.source.database.dremio.queries import DREMIO_SQL_STATEMENT
from metadata.ingestion.source.database.dremio.query_parser import DremioQueryParserSource
from metadata.ingestion.source.database.lineage_source import LineageSource


class DremioLineageSource(DremioQueryParserSource, LineageSource):
    """
    Dremio class for Lineage

    The lineage of a view, at table and column level, comes from the SQL of the
    view stored by the metadata workflow, which the parser of the parent class
    reads. The lineage of the tables that queries fill comes from the job
    history, limited to the statements that write.
    """

    sql_stmt = DREMIO_SQL_STATEMENT

    filters = """
        AND (
            lower("query") LIKE '%%create%%table%%as%%'
            OR lower("query") LIKE '%%insert%%into%%'
            OR lower("query") LIKE '%%merge%%into%%'
        )
    """
