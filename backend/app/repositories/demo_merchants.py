"""Persisted fictional merchant registry used by demo QR payments."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pymongo.errors import PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager


DEMO_MERCHANT_SEEDS: tuple[dict[str, str], ...] = (
    {
        "merchant_id": "MODI-CHAI-001",
        "merchant_name": "Modi Chai ki Tapri",
        "category": "Tea, Snacks and Refreshments",
        "demo_bank": "BJP Bank Demo",
        "merchant_account_id": "DEMO-MERCHANT-MODI-001",
    },
    {
        "merchant_id": "MELONI-CHOCO-002",
        "merchant_name": "Meloni ki Melodi Chocolate Shop",
        "category": "Chocolates and Snacks",
        "demo_bank": "BJP Bank Demo",
        "merchant_account_id": "DEMO-MERCHANT-MELONI-002",
    },
)


@runtime_checkable
class DemoMerchantRepositoryProtocol(Protocol):
    def get(self, merchant_id: str) -> dict[str, Any] | None: ...
    def list(self) -> tuple[dict[str, Any], ...]: ...
    def update_status(self, merchant_id: str, status: str) -> dict[str, Any] | None: ...


class DemoMerchantRepository(DemoMerchantRepositoryProtocol):
    """MongoDB current-state registry; QR payloads are projections of it."""

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["demo_merchants"]

    @staticmethod
    def _payload(document: dict[str, Any]) -> str:
        return json.dumps(
            {
                "type": "spendshield_demo_merchant",
                "qr_type": "SPENDSHIELD_DEMO_MERCHANT",
                "version": 1,
                "merchant_id": str(document["merchant_id"]),
                "merchant_name": str(document["merchant_name"]),
                "category": str(document["category"]),
                "demo_bank": str(document["demo_bank"]),
                "merchant_account_id": str(document["merchant_account_id"]),
                "status": str(document.get("status", "ACTIVE")),
                "simulation_only": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _document(cls, seed: dict[str, str]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            **seed,
            "merchant_name_key": " ".join(seed["merchant_name"].casefold().split()),
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
            "qr_payload": cls._payload({**seed, "status": "ACTIVE"}),
        }

    def _ensure_seeded(self) -> None:
        collection = self._collection()
        try:
            for seed in DEMO_MERCHANT_SEEDS:
                document = self._document(seed)
                existing = collection.find_one({"merchant_id": seed["merchant_id"]})
                if existing is None:
                    collection.insert_one(document)
                    continue
                # Catalog metadata is safe current-state data. Keep an admin's
                # ACTIVE/INACTIVE choice, but refresh the classroom label and
                # QR projection when the seed contract evolves.
                status = str(existing.get("status", "ACTIVE"))
                refreshed = {**seed, "status": status}
                collection.update_one(
                    {"merchant_id": seed["merchant_id"]},
                    {
                        "$set": {
                            "merchant_name": seed["merchant_name"],
                            "category": seed["category"],
                            "demo_bank": seed["demo_bank"],
                            "merchant_account_id": seed["merchant_account_id"],
                            "merchant_name_key": document["merchant_name_key"],
                            "updated_at": datetime.now(timezone.utc),
                            "qr_payload": self._payload(refreshed),
                        }
                    },
                )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def get(self, merchant_id: str) -> dict[str, Any] | None:
        self._ensure_seeded()
        try:
            return self._collection().find_one({"merchant_id": merchant_id})
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def list(self) -> tuple[dict[str, Any], ...]:
        self._ensure_seeded()
        try:
            return tuple(self._collection().find({}).sort("merchant_name_key", 1))
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def update_status(self, merchant_id: str, status: str) -> dict[str, Any] | None:
        current = self.get(merchant_id)
        if current is None:
            return None
        current["status"] = status
        current["updated_at"] = datetime.now(timezone.utc)
        current["qr_payload"] = self._payload(current)
        try:
            self._collection().update_one(
                {"merchant_id": merchant_id},
                {"$set": {"status": status, "updated_at": current["updated_at"], "qr_payload": current["qr_payload"]}},
            )
            return self.get(merchant_id)
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc


class UnavailableDemoMerchantRepository:
    def get(self, _: str) -> dict[str, Any] | None:
        raise DatabaseUnavailableError()

    def list(self) -> tuple[dict[str, Any], ...]:
        raise DatabaseUnavailableError()

    def update_status(self, _: str, __: str) -> dict[str, Any] | None:
        raise DatabaseUnavailableError()


__all__ = ["DEMO_MERCHANT_SEEDS", "DemoMerchantRepository", "UnavailableDemoMerchantRepository"]
