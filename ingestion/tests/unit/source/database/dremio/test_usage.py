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

from datetime import datetime

from metadata.ingestion.source.database.dremio.lineage import DremioLineageSource
from metadata.ingestion.source.database.dremio.service_spec import ServiceSpec
from metadata.ingestion.source.database.dremio.usage import DremioUsageSource
from metadata.ingestion.source.database.usage_source import UsageSource

START = datetime(2026, 9, 29, 0, 0, 0)
END = datetime(2026, 9, 30, 0, 0, 0)


class TestUsageSource:
    def test_it_is_a_usage_source(self):
        assert issubclass(DremioUsageSource, UsageSource)

    def test_spec_registers_the_usage_source(self):
        assert ServiceSpec.usage_source_class.endswith("dremio.usage.DremioUsageSource")

    def test_usage_and_lineage_share_the_statement_builder(self):
        assert DremioUsageSource.get_sql_statement is DremioLineageSource.get_sql_statement
