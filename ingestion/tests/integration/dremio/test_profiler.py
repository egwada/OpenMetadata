import pytest

from metadata.generated.schema.entity.data.table import ColumnProfile, TableProfile
from metadata.workflow.metadata import MetadataWorkflow
from metadata.workflow.profiler import ProfilerWorkflow


@pytest.fixture(scope="module")
def run_profiler(
    patch_passwords_for_db_services,
    run_workflow,
    ingestion_config,
    profiler_config,
):
    ingestion_config["source"]["sourceConfig"]["config"]["databaseFilterPattern"] = {
        "includes": ["^lake$", "^reporting$"]
    }
    run_workflow(MetadataWorkflow, ingestion_config)
    profiler_config["source"]["sourceConfig"]["config"]["databaseFilterPattern"] = {"includes": ["^lake$"]}
    run_workflow(ProfilerWorkflow, profiler_config)


def test_table_profile(run_profiler, metadata, db_service):
    service = db_service.fullyQualifiedName.root
    profiles = metadata.get_profile_data(
        f"{service}.lake.sales.customers",
        start_ts=0,
        end_ts=4_102_444_800_000,
        profile_type=TableProfile,
    ).entities

    assert profiles
    assert profiles[-1].rowCount == 2
    assert profiles[-1].columnCount == 3


def test_column_profiles(run_profiler, metadata, db_service):
    service = db_service.fullyQualifiedName.root
    profiles = metadata.get_profile_data(
        f"{service}.lake.sales.orders.amount",
        start_ts=0,
        end_ts=4_102_444_800_000,
        profile_type=ColumnProfile,
    ).entities

    assert profiles
    assert profiles[-1].valuesCount == 1
    assert profiles[-1].min == 12.5
    assert profiles[-1].max == 12.5
