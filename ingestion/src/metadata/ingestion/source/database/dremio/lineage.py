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

from typing import Iterator

from metadata.generated.schema.type.tableQuery import TableQuery
from metadata.ingestion.source.database.dremio.query_parser import DremioQueryParserSource
from metadata.ingestion.source.database.lineage_source import LineageSource
from metadata.utils.logger import ingestion_logger

logger = ingestion_logger()


class DremioLineageSource(DremioQueryParserSource, LineageSource):
    """
    Dremio class for Lineage

    The lineage of a view, at table and column level, comes from the SQL of the
    view stored by the metadata workflow, which the parser of the parent class
    reads. The lineage built from the query log is not implemented yet.
    """

    def yield_table_query(self) -> Iterator[TableQuery]:
        logger.info("Query lineage is not supported for Dremio yet, only the lineage of views is processed")
        yield from ()
