# Derived from https://github.com/TIKI-Institut/openmetadata-dremio-connector
# Copyright TIKI GmbH, licensed under the Apache License, Version 2.0.
# The queries below up to DREMIO_GET_VIEWS come from that project; the
# test-connection queries that follow were added for OpenMetadata.

"""
SQL queries used by the Dremio connector.

Dremio exposes spaces, sources and folders as schemas whose names are dotted
paths: `<space>.<folder>(.<folder>)`. A top-level name is a database for
OpenMetadata, and the remainder of the path is its schema.
"""

import textwrap

DREMIO_GET_DATABASES = textwrap.dedent(
    """
SELECT SCHEMA_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE SCHEMA_NAME NOT LIKE '%.%' 
  AND NOT STARTS_WITH(SCHEMA_NAME, '@') 
  AND NOT STARTS_WITH(SCHEMA_NAME, '$')
    """
)

DREMIO_GET_SCHEMAS = textwrap.dedent(
    """
SELECT SCHEMA_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE SCHEMA_NAME LIKE '{database_name}.%' 
    """
)


DREMIO_GET_TABLES = textwrap.dedent(
    """
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA."TABLES"
WHERE TABLE_SCHEMA  = '{schema_name}' 
AND TABLE_TYPE = 'TABLE'
    """
)

DREMIO_GET_VIEWS = textwrap.dedent(
    """
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA."TABLES"
WHERE TABLE_SCHEMA  = '{schema_name}' 
AND TABLE_TYPE = 'VIEW'
    """
)


# Test connection
DREMIO_TEST_GET_SCHEMAS = textwrap.dedent(
    """
SELECT SCHEMA_NAME
FROM INFORMATION_SCHEMA.SCHEMATA
    """
)

# `TABLE_SCHEMA <> 'INFORMATION_SCHEMA'` keeps the check on user datasets and
# off the system catalog that Dremio always exposes.
DREMIO_TEST_GET_TABLES = textwrap.dedent(
    """
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA."TABLES"
WHERE TABLE_TYPE IN ('TABLE', 'VIEW')
  AND TABLE_SCHEMA <> 'INFORMATION_SCHEMA'
    """
)

# The job history lives in a different system table depending on the edition:
# `sys.project.jobs` on Dremio Cloud, `sys.jobs` on Dremio Software. It is
# resolved at run time by probing these candidates in order.
DREMIO_JOBS_TABLES = ("sys.project.jobs", "sys.jobs")

DREMIO_TEST_GET_JOBS = "SELECT job_id FROM {jobs_table} LIMIT 1"
