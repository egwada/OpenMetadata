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
Dremio base for the Usage and Lineage workflows
"""

from abc import ABC
from datetime import datetime
from functools import cached_property
from typing import Optional

from metadata.generated.schema.entity.services.connections.database.dremioConnection import (
    DremioConnection as DremioConnectionConfig,
)
from metadata.generated.schema.metadataIngestion.workflow import (
    Source as WorkflowSource,
)
from metadata.ingestion.api.steps import InvalidSourceException
from metadata.ingestion.ometa.ometa_api import OpenMetadata
from metadata.ingestion.source.database.dremio.connection import get_jobs_table
from metadata.ingestion.source.database.dremio.queries import DREMIO_INTERNAL_QUERY_TYPES
from metadata.ingestion.source.database.query_parser_source import QueryParserSource

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class DremioQueryParserSource(QueryParserSource, ABC):
    """
    Dremio base for Usage and Lineage
    """

    @classmethod
    def create(cls, config_dict: dict, metadata: OpenMetadata, pipeline_name: Optional[str] = None):
        """Create class instance"""
        config: WorkflowSource = WorkflowSource.model_validate(config_dict)
        connection: DremioConnectionConfig = config.serviceConnection.root.config
        if not isinstance(connection, DremioConnectionConfig):
            raise InvalidSourceException(f"Expected DremioConnection, but got {connection}")
        return cls(config, metadata)

    @cached_property
    def jobs_table(self) -> str:
        """The system table that holds the job history of this edition of Dremio"""
        return get_jobs_table(self.engine)

    def get_sql_statement(self, start_time: datetime, end_time: datetime) -> str:
        """
        Returns the statement that reads the job history between the two dates
        """
        return self.sql_stmt.format(
            jobs_table=self.jobs_table,
            excluded_query_types=", ".join(f"'{query_type}'" for query_type in DREMIO_INTERNAL_QUERY_TYPES),
            start_time=start_time.strftime(TIMESTAMP_FORMAT),
            end_time=end_time.strftime(TIMESTAMP_FORMAT),
            filters=self.get_filters(),
            result_limit=self.source_config.resultLimit,
        )
