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
Unit tests for the Dremio lineage
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from metadata.generated.schema.entity.services.connections.database.dremioConnection import (
    DremioConnection as DremioConnectionConfig,
)
from metadata.ingestion.api.steps import InvalidSourceException
from metadata.ingestion.lineage.models import Dialect
from metadata.ingestion.lineage.parser import LineageParser
from metadata.ingestion.source.database.dremio.lineage import DremioLineageSource
from metadata.ingestion.source.database.dremio.queries import DREMIO_SQL_STATEMENT
from metadata.ingestion.source.database.dremio.service_spec import ServiceSpec
from metadata.ingestion.source.database.lineage_source import LineageSource

VIEW_SQL = """
SELECT o.order_id AS id, SUM(l.amount) AS total
FROM "space"."folder"."orders" o
JOIN "space"."folder"."lines" l ON l.order_id = o.order_id
GROUP BY o.order_id
"""


class TestLineageParsing:
    """
    What the lineage workflow does with the stored definition
    """

    @staticmethod
    def parse(sql: str) -> LineageParser:
        return LineageParser(sql, Dialect.ANSI, timeout_seconds=30)

    def test_create_view_gives_table_and_column_lineage(self):
        parser = self.parse(f'CREATE VIEW "totals" AS {VIEW_SQL}')

        assert {str(table) for table in parser.source_tables} == {"<default>.orders", "<default>.lines"} or len(
            parser.source_tables
        ) == 2
        assert parser.target_tables
        assert parser.column_lineage

    def test_a_bare_select_gives_no_column_lineage(self):
        # This is why the definition is wrapped in a CREATE VIEW
        parser = self.parse(VIEW_SQL)

        assert parser.source_tables
        assert not parser.column_lineage


class TestLineageSource:
    def test_it_is_a_lineage_source(self):
        assert issubclass(DremioLineageSource, LineageSource)

    def test_spec_registers_the_lineage_source(self):
        assert ServiceSpec.lineage_source_class.endswith("dremio.lineage.DremioLineageSource")

    def test_query_lineage_reads_the_job_history(self):
        assert DremioLineageSource.sql_stmt is DREMIO_SQL_STATEMENT

    def test_query_lineage_is_not_overridden(self):
        assert "yield_table_query" not in DremioLineageSource.__dict__

    @pytest.mark.parametrize("pattern", ["create%%table%%as", "insert%%into", "merge%%into"])
    def test_only_statements_that_write_are_selected(self, pattern):
        assert f"LIKE '%%{pattern}%%'" in DremioLineageSource.filters

    def test_filter_is_added_to_the_statement(self):
        source = DremioLineageSource.__new__(DremioLineageSource)
        source.engine = MagicMock()
        source.__dict__["jobs_table"] = "sys.jobs_recent"
        source.source_config = MagicMock(resultLimit=10, filterCondition=None)

        statement = source.get_sql_statement(datetime(2026, 9, 29), datetime(2026, 9, 30))

        assert "FROM sys.jobs_recent" in statement
        assert "create%%table%%as" in statement

    def test_create_builds_a_source_from_a_dremio_connection(self):
        config = MagicMock()
        config.serviceConnection.root.config = DremioConnectionConfig.model_validate(
            {"authType": {"hostPort": "http://dremio:9047", "username": "u", "password": "p"}}
        )

        with (
            patch("metadata.ingestion.source.database.dremio.query_parser.WorkflowSource") as workflow_source,
            patch.object(DremioLineageSource, "__init__", return_value=None),
        ):
            workflow_source.model_validate.return_value = config

            assert isinstance(DremioLineageSource.create({}, MagicMock()), DremioLineageSource)

    def test_create_rejects_another_connection(self):
        with patch("metadata.ingestion.source.database.dremio.query_parser.WorkflowSource") as workflow_source:
            workflow_source.model_validate.return_value.serviceConnection.root.config = object()

            with pytest.raises(InvalidSourceException, match="Expected DremioConnection"):
                DremioLineageSource.create({}, MagicMock())
