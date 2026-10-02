# Dremio

In this section, we provide guides and references to use the Dremio connector.

## Requirements

The connector reads Dremio through its Arrow Flight SQL interface, with `INFORMATION_SCHEMA` and `DESCRIBE`. Both Dremio Software and Dremio Cloud are supported.

- **Dremio Software**: the user must be able to read the datasets to ingest (a space or a source that the user cannot see is not ingested), and to read `sys.jobs_recent` for the usage and the lineage built from queries. Arrow Flight must be reachable on port `32010` of the host of the URL.
- **Dremio Cloud**: the personal access token must belong to a user who can read the datasets, and `sys.project.jobs_recent` for the usage and the lineage built from queries.

The metadata workflow stores the SQL of the views, and the lineage workflow reads it: run the metadata workflow first. The spaces of the home of a user (`@user`) and `$scratch` are not ingested.

You can find further information on the Dremio connector in the <a href="https://docs.open-metadata.org/connectors/database/dremio" target="_blank">docs</a>.

## Connection Details

$$section
### Host and Port $(id="hostPort")

Dremio Software only. URL of the REST API of the Dremio coordinator, including the protocol and the port (e.g. `http://localhost:9047` or `https://dremio.example.com:9047`). The connector reaches Arrow Flight on port `32010` of the same host, with TLS when the URL is `https`.
$$

$$section
### Username $(id="username")

Dremio Software only. User to connect to Dremio. This user should have privileges to read the metadata of the datasets to ingest.
$$

$$section
### Password $(id="password")

Dremio Software only. Password of the user.
$$

$$section
### Verify SSL $(id="verifySSL")

Dremio Software only, when Host and Port is an `https` URL. How the certificate of the Dremio server is checked:
- `no-ssl` (default): against the trusted authorities of the system.
- `ignore`: not checked. Use it for a self-signed certificate. The connection is encrypted but the server is not authenticated: prefer `validate` where you can.
- `validate`: against the CA certificate of the SSL Config.
$$

$$section
### SSL Config $(id="sslConfig")

Dremio Software only. The CA certificate that signed the certificate of the Dremio server (PEM), used when Verify SSL is `validate`.
$$

$$section
### Region $(id="region")

Dremio Cloud only. Region of your organization: `US` or `EU`. It selects the Arrow Flight endpoint of the region.
$$

$$section
### Personal Access Token $(id="personalAccessToken")

Dremio Cloud only. Personal access token of the user, generated in your account settings. The datasets are read from the default project of the token.
$$

$$section
### Project ID $(id="projectId")

Dremio Cloud only. Identifier of the project. It can be found in the URL or the settings of the project.
$$

$$section
### Namespace $(id="database")

Optional. A space or a source (the first part of the path of a dataset) to restrict the ingestion to. When left blank, all the namespaces are ingested. A Dremio namespace is a database in OpenMetadata, and its folders are schemas: `sales.reports.monthly` is the table `monthly` of the schema `reports` of the database `sales`. The tables and views at the root of a namespace are in a schema that has the name of the namespace.
$$

$$section
### Namespace Filter Pattern $(id="databaseFilterPattern")

Regex to only include or exclude the namespaces (spaces and sources) that match the pattern.
$$

$$section
### Folder Filter Pattern $(id="schemaFilterPattern")

Regex to only include or exclude the folders that match the pattern. A nested folder is named with its path, e.g. `reports.monthly`.
$$

$$section
### Table Filter Pattern $(id="tableFilterPattern")

Regex to only include or exclude the tables and views that match the pattern.
$$
