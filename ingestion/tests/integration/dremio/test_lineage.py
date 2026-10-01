import pytest

from metadata.generated.schema.entity.data.table import Table
from metadata.workflow.metadata import MetadataWorkflow


@pytest.fixture(scope="module")
def ingested_tables(patch_passwords_for_db_services, run_workflow, ingestion_config, db_service):
    ingestion_config["source"]["sourceConfig"]["config"]["databaseFilterPattern"] = {
        "includes": ["^lake$", "^reporting$"]
    }
    run_workflow(MetadataWorkflow, ingestion_config)


@pytest.fixture(scope="module")
def run_view_lineage(ingested_tables, run_workflow, ingestion_config):
    lineage_config = {
        **ingestion_config,
        "source": {
            **ingestion_config["source"],
            "type": "dremio-lineage",
            "sourceConfig": {"config": {"type": "DatabaseLineage", "overrideViewLineage": True}},
        },
    }
    run_workflow(MetadataWorkflow, lineage_config)


def test_view_has_lineage_from_its_tables(run_view_lineage, metadata, db_service):
    service = db_service.fullyQualifiedName.root
    view = metadata.get_by_name(entity=Table, fqn=f"{service}.reporting.reporting.customer_totals")
    lineage = metadata.get_lineage_by_id(Table, str(view.id.root), up_depth=1, down_depth=0)

    upstream = {node["fullyQualifiedName"] for node in lineage["nodes"]}
    assert f"{service}.lake.sales.customers" in upstream
    assert f"{service}.lake.sales.orders" in upstream


def test_view_has_column_lineage(run_view_lineage, metadata, db_service):
    service = db_service.fullyQualifiedName.root
    view = metadata.get_by_name(entity=Table, fqn=f"{service}.reporting.reporting.customer_totals")
    lineage = metadata.get_lineage_by_id(Table, str(view.id.root), up_depth=1, down_depth=0)

    column_pairs = {
        (from_column, column_lineage["toColumn"])
        for edge in lineage["upstreamEdges"]
        for column_lineage in edge.get("lineageDetails", {}).get("columnsLineage", [])
        for from_column in column_lineage["fromColumns"]
    }
    assert (
        f"{service}.lake.sales.customers.name",
        f"{service}.reporting.reporting.customer_totals.name",
    ) in column_pairs
    assert (
        f"{service}.lake.sales.orders.amount",
        f"{service}.reporting.reporting.customer_totals.total",
    ) in column_pairs


def test_view_built_on_a_view_of_a_space_has_lineage(run_view_lineage, metadata, db_service):
    service = db_service.fullyQualifiedName.root
    view = metadata.get_by_name(entity=Table, fqn=f"{service}.reporting.reporting.top_customers")
    lineage = metadata.get_lineage_by_id(Table, str(view.id.root), up_depth=1, down_depth=0)

    upstream = {node["fullyQualifiedName"] for node in lineage["nodes"]}
    assert f"{service}.reporting.reporting.customer_totals" in upstream
