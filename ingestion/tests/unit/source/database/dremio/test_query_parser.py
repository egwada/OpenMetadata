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
Unit tests for the Dremio usage
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from metadata.ingestion.source.database.dremio.lineage import DremioLineageSource
from metadata.ingestion.source.database.dremio.queries import (
    DREMIO_INTERNAL_QUERY_TYPES,
    DREMIO_JOBS_TABLES,
)

START = datetime(2026, 9, 29, 0, 0, 0)
END = datetime(2026, 9, 30, 0, 0, 0)


def lineage_source(filters: str = "", result_limit: int = 1000) -> DremioLineageSource:
    source = DremioLineageSource.__new__(DremioLineageSource)
    source.engine = MagicMock()
    source.source_config = MagicMock(resultLimit=result_limit, filterCondition=None)
    source.filters = filters
    return source


class TestJobsTable:
    def test_history_tables_are_not_the_running_jobs_ones(self):
        # sys.jobs only lists the running jobs, the history is in jobs_recent
        assert all(table.endswith("jobs_recent") for table in DREMIO_JOBS_TABLES)

    def test_table_is_resolved_once(self):
        source = lineage_source()

        with patch(
            "metadata.ingestion.source.database.dremio.query_parser.get_jobs_table",
            return_value="sys.jobs_recent",
        ) as resolve:
            assert source.jobs_table == "sys.jobs_recent"
            assert source.jobs_table == "sys.jobs_recent"

        resolve.assert_called_once_with(source.engine)


class TestStatement:
    @staticmethod
    def statement(jobs_table: str = "sys.jobs_recent", **kwargs) -> str:
        source = lineage_source(**kwargs)
        source.__dict__["jobs_table"] = jobs_table
        return source.get_sql_statement(START, END)

    def test_reads_the_job_history_of_the_edition(self):
        assert "FROM sys.project.jobs_recent" in self.statement("sys.project.jobs_recent")

    def test_only_completed_jobs(self):
        assert "status = 'COMPLETED'" in self.statement()

    def test_dates_are_written_without_time_zone(self):
        statement = self.statement()

        assert "submitted_ts >= TIMESTAMP '2026-09-29 00:00:00'" in statement
        assert "submitted_ts < TIMESTAMP '2026-09-30 00:00:00'" in statement

    def test_aware_dates_are_written_without_time_zone(self):
        source = lineage_source()
        source.__dict__["jobs_table"] = "sys.jobs_recent"

        statement = source.get_sql_statement(START.replace(tzinfo=timezone.utc), END.replace(tzinfo=timezone.utc))

        assert "TIMESTAMP '2026-09-29 00:00:00'" in statement

    def test_internal_jobs_are_left_out(self):
        statement = self.statement()

        for query_type in DREMIO_INTERNAL_QUERY_TYPES:
            assert f"'{query_type}'" in statement
        assert "query_type NOT IN (" in statement

    def test_result_limit(self):
        assert self.statement(result_limit=50).rstrip().endswith("LIMIT 50")

    def test_columns_expected_by_the_usage_workflow(self):
        statement = self.statement()

        for column in ("AS query_text", "user_name", "AS start_time", "AS end_time", "AS duration"):
            assert column in statement

    def test_filter_condition_is_added(self):
        assert "AND user_name = 'svc'" in self.statement(filters="AND user_name = 'svc'")
