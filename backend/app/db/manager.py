"""Connection lifecycle and dependency health for MongoDB and Cassandra."""

from __future__ import annotations

from typing import Any

from cassandra import DriverException
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.cluster import NoHostAvailable
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.core.exceptions import (
    DatabaseNotConfiguredError,
    DatabaseUnavailableError,
)
from app.core.logging import get_logger
from app.db.cassandra_schema import ensure_cassandra_schema
from app.db.mongo_schema import ensure_mongo_schema

LOGGER = get_logger(__name__)


class DatabaseManager:
    """Own MongoDB/Cassandra clients without exposing driver details to routes."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._mongo_client: MongoClient[Any] | None = None
        self._mongo_database: Any | None = None
        self._cassandra_cluster: Cluster | None = None
        self._cassandra_session: Any | None = None

    @property
    def mongo_database(self) -> Any:
        """Return a connected MongoDB database handle."""

        self.connect_mongodb()
        assert self._mongo_database is not None
        return self._mongo_database

    @property
    def cassandra_session(self) -> Any:
        """Return a connected Cassandra session."""

        self.connect_cassandra()
        assert self._cassandra_session is not None
        return self._cassandra_session

    def connect_mongodb(self) -> Any:
        """Connect to MongoDB and verify it with a ping."""

        if self._mongo_database is not None:
            return self._mongo_database
        uri = (self.settings.mongodb_uri or "").strip()
        if not uri:
            raise DatabaseNotConfiguredError()
        try:
            client_options: dict[str, Any] = {
                "serverSelectionTimeoutMS": self.settings.mongodb_server_selection_timeout_ms,
                "connectTimeoutMS": self.settings.mongodb_connect_timeout_ms,
                "tz_aware": True,
            }
            replica_set = (self.settings.mongodb_replica_set or "").strip()
            if replica_set:
                client_options["replicaSet"] = replica_set
            client = MongoClient(uri, **client_options)
            client.admin.command("ping")
            self._mongo_client = client
            self._mongo_database = client[self.settings.mongodb_database]
            return self._mongo_database
        except PyMongoError as exc:
            LOGGER.exception("database_connection_failed database=mongodb")
            if "client" in locals():
                client.close()
            raise DatabaseUnavailableError() from exc

    def connect_cassandra(self) -> Any:
        """Connect to Cassandra and select the configured keyspace."""

        if self._cassandra_session is not None:
            return self._cassandra_session
        hosts = [
            host.strip()
            for host in (self.settings.cassandra_hosts or "").split(",")
            if host.strip()
        ]
        if not hosts:
            raise DatabaseNotConfiguredError()

        auth_provider = None
        if self.settings.cassandra_username and self.settings.cassandra_password:
            auth_provider = PlainTextAuthProvider(
                username=self.settings.cassandra_username,
                password=self.settings.cassandra_password,
            )
        try:
            cluster = Cluster(
                contact_points=hosts,
                port=self.settings.cassandra_port,
                auth_provider=auth_provider,
                connect_timeout=self.settings.cassandra_connect_timeout_seconds,
            )
            session = cluster.connect()
            session.execute(
                f"CREATE KEYSPACE IF NOT EXISTS {self.settings.cassandra_keyspace} "
                "WITH replication = "
                f"{{'class': 'SimpleStrategy', 'replication_factor': "
                f"'{self.settings.cassandra_replication_factor}'}}"
            )
            session.set_keyspace(self.settings.cassandra_keyspace)
            self._cassandra_cluster = cluster
            self._cassandra_session = session
            return session
        except (DriverException, NoHostAvailable, OSError) as exc:
            LOGGER.exception("database_connection_failed database=cassandra")
            if "cluster" in locals():
                cluster.shutdown()
            raise DatabaseUnavailableError() from exc

    def ensure_mongodb_schema(self) -> dict[str, int]:
        """Apply MongoDB collections and indexes."""

        return ensure_mongo_schema(self.mongo_database)

    def ensure_cassandra_schema(self) -> dict[str, int]:
        """Apply Cassandra event tables."""

        return ensure_cassandra_schema(
            self.cassandra_session,
            self.settings.cassandra_keyspace,
            self.settings.cassandra_replication_factor,
        )

    def initialize_schema(self) -> dict[str, dict[str, int]]:
        """Connect to both databases and initialize their Phase 2 schemas."""

        return {
            "mongodb": self.ensure_mongodb_schema(),
            "cassandra": self.ensure_cassandra_schema(),
        }

    def health(self) -> dict[str, Any]:
        """Return safe dependency status and non-secret deployment identity."""

        checks: dict[str, dict[str, str]] = {}
        checks["mongodb"] = self._check_mongodb()
        checks["cassandra"] = self._check_cassandra()
        overall = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
        return {"status": overall, "checks": checks}

    def _check_mongodb(self) -> dict[str, str]:
        if not (self.settings.mongodb_uri or "").strip():
            return {"status": "not_configured", "detail": "MongoDB is not configured."}
        try:
            database = self.connect_mongodb()
            hello = database.client.admin.command("hello")
            primary = database.client.primary
            endpoint = (
                f"{primary[0]}:{primary[1]}" if primary is not None else None
            )
            return {
                "status": "ok",
                "detail": "MongoDB is reachable.",
                "endpoint": endpoint,
                "replica_set": hello.get("setName"),
                "is_writable_primary": bool(hello.get("isWritablePrimary")),
            }
        except Exception:
            LOGGER.exception("database_health_failed database=mongodb")
            return {"status": "unavailable", "detail": "MongoDB is unavailable."}

    def _check_cassandra(self) -> dict[str, str]:
        if not (self.settings.cassandra_hosts or "").strip():
            return {"status": "not_configured", "detail": "Cassandra is not configured."}
        try:
            self.connect_cassandra().execute("SELECT release_version FROM system.local")
            return {"status": "ok", "detail": "Cassandra is reachable."}
        except Exception:
            LOGGER.exception("database_health_failed database=cassandra")
            return {"status": "unavailable", "detail": "Cassandra is unavailable."}

    def close(self) -> None:
        """Close database clients owned by this manager."""

        if self._cassandra_cluster is not None:
            self._cassandra_cluster.shutdown()
        if self._mongo_client is not None:
            self._mongo_client.close()
        self._cassandra_cluster = None
        self._cassandra_session = None
        self._mongo_client = None
        self._mongo_database = None


__all__ = ["DatabaseManager"]
