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
Unit tests for the Dremio SQLAlchemy dialect
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import types
from sqlalchemy.dialects import registry

from metadata.ingestion.source.database.dremio.dialect import (
    DremioFlightDialect,
    get_column_type,
    literal,
    quote_path,
)


def connection_returning(*rows) -> MagicMock:
    connection = MagicMock()
    result = connection.exec_driver_sql.return_value
    result.__iter__.side_effect = lambda: iter(rows)
    result.scalar.return_value = rows[0][0] if rows else None
    return connection


def executed_sql(connection: MagicMock) -> str:
    return connection.exec_driver_sql.call_args.args[0]


class TestQuoting:
    def test_literal_doubles_single_quotes(self):
        assert literal("o'brien") == "'o''brien'"

    def test_path_quotes_every_folder(self):
        assert quote_path("space.folder.sub", "table") == '"space"."folder"."sub"."table"'

    def test_path_without_schema_is_the_table(self):
        assert quote_path(None, "table") == '"table"'
        assert quote_path("", "table") == '"table"'

    def test_path_doubles_double_quotes(self):
        assert quote_path("space", 'my"table') == '"space"."my""table"'


class TestColumnType:
    @pytest.mark.parametrize(
        "data_type,expected",
        [
            ("BOOLEAN", types.BOOLEAN),
            ("INTEGER", types.INTEGER),
            ("BIGINT", types.BIGINT),
            ("FLOAT", types.FLOAT),
            ("DOUBLE", types.DOUBLE),
            ("DATE", types.DATE),
            ("TIME", types.TIME),
            ("TIMESTAMP", types.TIMESTAMP),
            ("BINARY VARYING", types.VARBINARY),
            ("CHARACTER VARYING", types.VARCHAR),
        ],
    )
    def test_dremio_types(self, data_type, expected):
        assert isinstance(get_column_type(data_type, None, None, None), expected)

    def test_types_are_case_insensitive(self):
        assert isinstance(get_column_type("bigint", None, None, None), types.BIGINT)

    def test_varchar_keeps_its_length(self):
        assert get_column_type("CHARACTER VARYING", 255, None, None).length == 255

    def test_decimal_accepts_the_floats_dremio_reports(self):
        column_type = get_column_type("DECIMAL", None, 38.0, 2.0)

        assert (column_type.precision, column_type.scale) == (38, 2)

    def test_decimal_without_scale(self):
        assert get_column_type("DECIMAL", None, 10.0, None).scale == 0

    def test_intervals(self):
        assert isinstance(get_column_type("INTERVAL DAY TO SECOND", None, None, None), types.Interval)

    def test_nested_types_are_not_reflected(self):
        assert isinstance(get_column_type("ROW", None, None, None), types.NullType)


class TestReflection:
    dialect = DremioFlightDialect()

    def test_columns_are_read_with_describe(self):
        connection = connection_returning(
            ("region", "CHARACTER VARYING", "YES", None, None),
            ("amount", "DECIMAL", "NO", 12.0, 2.0),
        )

        columns = self.dialect.get_columns(connection, "sales", "polaris.demo")

        assert executed_sql(connection) == 'DESCRIBE "polaris"."demo"."sales"'
        assert [(c["name"], c["nullable"]) for c in columns] == [("region", True), ("amount", False)]
        assert isinstance(columns[0]["type"], types.VARCHAR)
        assert (columns[1]["type"].precision, columns[1]["type"].scale) == (12, 2)

    def test_describe_extra_columns_are_ignored(self):
        connection = connection_returning(("id", "BIGINT", "YES", None, None, "[]", None, None))

        assert self.dialect.get_columns(connection, "t", "s")[0]["name"] == "id"

    def test_view_definition_is_read_from_the_catalog(self):
        connection = connection_returning(("SELECT 1",))

        definition = self.dialect.get_view_definition(connection, "v", "space.folder")

        assert definition == "SELECT 1"
        assert "INFORMATION_SCHEMA.\"VIEWS\"" in executed_sql(connection)
        assert "TABLE_SCHEMA = 'space.folder'" in executed_sql(connection)
        assert "TABLE_NAME = 'v'" in executed_sql(connection)

    def test_names_with_quotes_cannot_break_out_of_the_statement(self):
        connection = connection_returning(("SELECT 1",))

        self.dialect.get_view_definition(connection, "v' OR '1'='1", "s")

        assert "TABLE_NAME = 'v'' OR ''1''=''1'" in executed_sql(connection)

    def test_names_with_a_colon_are_not_read_as_bind_parameters(self):
        connection = connection_returning(("SELECT 1",))

        self.dialect.get_view_definition(connection, "a:b", "s")

        connection.exec_driver_sql.assert_called_once()
        connection.execute.assert_not_called()

    def test_schema_names(self):
        connection = connection_returning(("space",), ("space.folder",))

        assert self.dialect.get_schema_names(connection) == ["space", "space.folder"]

    def test_table_names(self):
        connection = connection_returning(("a",), ("b",))

        assert self.dialect.get_table_names(connection, "space.folder") == ["a", "b"]
        assert "TABLE_SCHEMA = 'space.folder'" in executed_sql(connection)

    def test_has_table(self):
        assert self.dialect.has_table(connection_returning((1,)), "t", "s") is True
        assert self.dialect.has_table(connection_returning((0,)), "t", "s") is False


def test_dialect_replaces_the_one_of_the_driver():
    assert registry.load("dremio.flight") is DremioFlightDialect
