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
Source connection handler
"""

from urllib.parse import urlparse

from sqlalchemy.engine import URL, Engine

from metadata.generated.schema.entity.services.connections.database.dremio.cloudAuth import (
    DremioCloudAuthentication,
    Region,
)
from metadata.generated.schema.entity.services.connections.database.dremio.softwareAuth import (
    DremioSoftwareAuthentication,
)
from metadata.generated.schema.entity.services.connections.database.dremioConnection import (
    DremioConnection as DremioConnectionConfig,
)
from metadata.ingestion.connections.builders import create_generic_db_connection
from metadata.ingestion.connections.connection import BaseConnection

DREMIO_DIALECT = "dremio+flight"

# Dremio Software serves Arrow Flight on its own port, next to the REST API
# that `hostPort` points to.
SOFTWARE_FLIGHT_PORT = 32010

# Dremio Cloud serves Arrow Flight over TLS on the regional data endpoint.
CLOUD_FLIGHT_HOSTS = {
    Region.US: "data.dremio.cloud",
    Region.EU: "data.eu.dremio.cloud",
}
CLOUD_FLIGHT_PORT = 443


class DremioConnection(BaseConnection[DremioConnectionConfig, Engine]):
    """
    Owns the SQLAlchemy engine used to read Dremio through Arrow Flight.
    """

    def _get_client(self) -> Engine:
        engine = create_generic_db_connection(
            connection=self.service_connection,
            get_connection_url_fn=get_connection_url,
            # The Dremio connection has no `connectionArguments` to forward.
            get_connection_args_fn=lambda _: {},
        )
        self._on_close(engine.dispose)
        return engine


def get_connection_url(connection: DremioConnectionConfig) -> URL:
    """
    Build the SQLAlchemy URL for the `sqlalchemy-dremio` Arrow Flight dialect.

    Dremio Software authenticates with a username and a password. Dremio Cloud
    authenticates with a Personal Access Token, sent as the `Token` option.
    """
    auth = connection.authType

    if isinstance(auth, DremioSoftwareAuthentication):
        # `hostPort` is the URL of the REST API (e.g. http://dremio:9047),
        # while the driver talks to the Arrow Flight port of the same host.
        rest_url = urlparse(str(auth.hostPort))
        return URL.create(
            drivername=DREMIO_DIALECT,
            username=auth.username,
            password=auth.password.get_secret_value(),
            host=rest_url.hostname,
            port=SOFTWARE_FLIGHT_PORT,
            query={"UseEncryption": str(rest_url.scheme == "https")},
        )

    if isinstance(auth, DremioCloudAuthentication):
        return URL.create(
            drivername=DREMIO_DIALECT,
            host=CLOUD_FLIGHT_HOSTS[auth.region],
            port=CLOUD_FLIGHT_PORT,
            query={
                "UseEncryption": "True",
                "Token": auth.personalAccessToken.get_secret_value(),
            },
        )

    raise ValueError(f"Unsupported Dremio authentication type: {type(auth).__name__}")
