import time

import pytest

from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.metadataIngestion.databaseServiceQueryUsagePipeline import (
    DatabaseUsageConfigType,
)
from metadata.workflow.metadata import MetadataWorkflow
from metadata.workflow.usage import UsageWorkflow

JOBS_WAIT_SECONDS = 120


@pytest.fixture(scope="module")
def queries_in_the_job_history(dremio_rest, dremio_data):
    """Reads of the two tables, kept by Dremio in its job history."""
    for _ in range(3):
        dremio_rest.run_sql("SELECT name FROM lake.sales.customers")
    dremio_rest.run_sql("SELECT amount FROM lake.sales.orders")


@pytest.fixture(scope="module")
def usage_config(sink_config, workflow_config, db_service, tmp_path_factory):
    staging = str(tmp_path_factory.mktemp("dremio_usage") / "dremio_usage")
    return {
        "source": {
            "type": "dremio-usage",
            "serviceName": db_service.fullyQualifiedName.root,
            "sourceConfig": {"config": {"type": DatabaseUsageConfigType.DatabaseUsage.value}},
        },
        "processor": {"type": "query-parser", "config": {}},
        "stage": {"type": "table-usage", "config": {"filename": staging}},
        "bulkSink": {"type": "metadata-usage", "config": {"filename": staging}},
        "sink": sink_config,
        "workflowConfig": workflow_config,
    }


@pytest.fixture(scope="module")
def run_usage(
    patch_passwords_for_db_services,
    queries_in_the_job_history,
    run_workflow,
    ingestion_config,
    usage_config,
    metadata,
    db_service,
):
    ingestion_config["source"]["sourceConfig"]["config"]["databaseFilterPattern"] = {
        "includes": ["^lake$", "^reporting$"]
    }
    run_workflow(MetadataWorkflow, ingestion_config)
    service = db_service.fullyQualifiedName.root
    customers_fqn = f"{service}.lake.sales.customers"
    # The job history of Dremio lags a little behind the jobs.
    deadline = time.time() + JOBS_WAIT_SECONDS
    while True:
        run_workflow(UsageWorkflow, usage_config)
        customers = metadata.get_by_name(entity=Table, fqn=customers_fqn, fields=["usageSummary"])
        if (customers.usageSummary and customers.usageSummary.dailyStats.count) or time.time() > deadline:
            return
        time.sleep(5)


def test_tables_read_by_queries_have_usage(run_usage, metadata, db_service):
    service = db_service.fullyQualifiedName.root

    customers = metadata.get_by_name(entity=Table, fqn=f"{service}.lake.sales.customers", fields=["usageSummary"])
    orders = metadata.get_by_name(entity=Table, fqn=f"{service}.lake.sales.orders", fields=["usageSummary"])

    assert customers.usageSummary.dailyStats.count >= 3
    assert orders.usageSummary.dailyStats.count >= 1
    assert customers.usageSummary.dailyStats.count > orders.usageSummary.dailyStats.count
