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
Unit tests for what the profiler and the data quality tests need from Dremio
"""

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, func, select

from metadata.generated.schema.entity.services.connections.database.dremioConnection import (
    DremioConnection as DremioConnectionConfig,
)
from metadata.ingestion.source.database.dremio.connection import get_connection_url
from metadata.ingestion.source.database.dremio.dialect import DremioFlightDialect
from metadata.profiler.orm.functions.length import LenFn
from metadata.profiler.orm.functions.modulo import ModuloFn
from metadata.profiler.orm.registry import Dialects

dialect = DremioFlightDialect()
sales = Table(
    "sales",
    MetaData(),
    Column("id", Integer),
    Column("region", String),
    schema="demo",
)


def compiled(statement) -> str:
    return " ".join(str(statement.compile(dialect=dialect)).split())


class TestDialectName:
    def test_profiler_rules_are_registered_for_dremio(self):
        assert dialect.name == Dialects.Dremio == "dremio"

    def test_the_driver_is_flight(self):
        assert dialect.driver == "flight"


class TestBindParameters:
    """The driver drops the parameters of a statement, they must be in the text"""

    def test_numbers_are_written_in_the_statement(self):
        statement = compiled(select(func.count()).select_from(sales).where(sales.c.id == 5).limit(1))

        assert "?" not in statement
        assert "id = 5" in statement
        assert "LIMIT 1" in statement

    def test_strings_are_written_and_escaped(self):
        statement = compiled(select(sales.c.id).where(sales.c.region == "o'brien"))

        assert "?" not in statement
        assert "region = 'o''brien'" in statement

    def test_a_null_is_written(self):
        statement = compiled(select(sales.c.id).where(sales.c.region.is_(None)))

        assert "region IS NULL" in statement

    def test_the_schema_is_written_as_a_quoted_path(self):
        assert compiled(select(sales.c.id)).endswith('FROM "demo"."sales"')


class TestProfilerFunctions:
    def test_length_is_length_and_not_len(self):
        # Dremio has no LEN function
        statement = compiled(select(LenFn(sales.c.region)))

        assert "LENGTH(" in statement
        assert "LEN(" not in statement.replace("LENGTH(", "")

    def test_modulo_is_a_function_and_not_an_operator(self):
        statement = compiled(select(ModuloFn(sales.c.id, 10)))

        assert "MOD(" in statement
        assert "%" not in statement


class TestSessionSchema:
    @pytest.mark.parametrize(
        "auth",
        [
            {"hostPort": "http://dremio:9047", "username": "u", "password": "p"},
            {"region": "EU", "personalAccessToken": "t", "projectId": "x"},
        ],
    )
    def test_the_namespace_is_the_default_schema_of_the_session(self, auth):
        # The profiler writes `folder.table`, which Dremio resolves from this schema
        url = get_connection_url(DremioConnectionConfig.model_validate({"authType": auth, "database": "polaris"}))

        assert url.database == "polaris"

    def test_without_a_namespace_there_is_no_default_schema(self):
        auth = {"hostPort": "http://dremio:9047", "username": "u", "password": "p"}

        assert get_connection_url(DremioConnectionConfig.model_validate({"authType": auth})).database is None
