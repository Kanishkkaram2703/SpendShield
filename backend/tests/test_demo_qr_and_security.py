"""Unit coverage for the persisted demo QR contract and demo MPIN boundary."""

from uuid import uuid4

import pytest

from app.api.v1.payments import _qr_category_snapshot, _resolve_qr_merchant
from app.core.exceptions import AppError
from app.domain.demo_payments import validate_demo_qr_payload
from app.services.demo_security_service import reset_demo_mpin, set_demo_mpin, verify_demo_mpin


class FakeMerchantRegistry:
    def __init__(self, record: dict):
        self.record = record

    def get(self, merchant_id: str):
        return self.record if merchant_id == self.record["merchant_id"] else None


class FakeSecurityRepository:
    def __init__(self):
        self.records = {}

    def get(self, owner_id: str, resource_id: str):
        return self.records.get((owner_id, resource_id))

    def create(self, owner_id: str, values: dict):
        self.records[(owner_id, values["user_id"])] = {**values}
        return self.records[(owner_id, values["user_id"])]

    def update(self, owner_id: str, resource_id: str, values: dict):
        self.records[(owner_id, resource_id)].update(values)
        return self.records[(owner_id, resource_id)]


def merchant_record() -> dict:
    return {
        "merchant_id": "MODI-CHAI-001",
        "merchant_name": "Modi Chai ki Tapri",
        "category": "Food and Beverages",
        "demo_bank": "BJP Bank Demo",
        "merchant_account_id": "DEMO-MERCHANT-MODI-001",
        "status": "ACTIVE",
    }


def qr_payload(record: dict) -> str:
    return (
        '{"type":"spendshield_demo_merchant","qr_type":"SPENDSHIELD_DEMO_MERCHANT",'
        '"simulation_only":true,"version":1,'
        f'"merchant_id":"{record["merchant_id"]}",'
        f'"merchant_name":"{record["merchant_name"]}",'
        f'"category":"{record["category"]}",'
        f'"demo_bank":"{record["demo_bank"]}",'
        f'"merchant_account_id":"{record["merchant_account_id"]}",'
        '"status":"ACTIVE"}'
    )


def test_versioned_qr_resolves_only_through_registered_merchant() -> None:
    record = merchant_record()
    parsed = validate_demo_qr_payload(qr_payload(record))
    resolved = _resolve_qr_merchant(qr_payload(record), FakeMerchantRegistry(record))
    assert parsed["version"] == 1
    assert resolved["merchant_id"] == record["merchant_id"]
    assert resolved["merchant_account_id"] == record["merchant_account_id"]

    with pytest.raises(AppError) as error:
        _resolve_qr_merchant(qr_payload({**record, "merchant_id": "UNKNOWN-999"}), FakeMerchantRegistry(record))
    assert error.value.code == "demo_merchant_not_found"


def test_versioned_qr_builds_a_complete_transaction_category_snapshot() -> None:
    snapshot = _qr_category_snapshot(merchant_record())

    assert snapshot == {
        "category_id": "demo-merchant",
        "category_name": "Food and Beverages",
        "subcategory_id": "merchant-modi-chai-001",
        "subcategory_name": "Demo merchant",
    }


def test_invalid_qr_returns_a_specific_safe_validation_error() -> None:
    with pytest.raises(AppError) as error:
        _resolve_qr_merchant("not-json", FakeMerchantRegistry(merchant_record()))

    assert error.value.code == "demo_qr_malformed"
    assert error.value.status_code == 422


def test_demo_mpin_is_hashed_and_repeated_failures_lock_it() -> None:
    repository = FakeSecurityRepository()
    owner_id = str(uuid4())
    set_demo_mpin(repository, owner_id, pin="123456")
    assert repository.records[(owner_id, owner_id)]["pin_hash"] != "123456"
    verify_demo_mpin(repository, owner_id, "123456")

    for _ in range(5):
        with pytest.raises(AppError) as error:
            verify_demo_mpin(repository, owner_id, "654321")
        assert error.value.code == "demo_mpin_invalid"
    with pytest.raises(AppError) as locked:
        verify_demo_mpin(repository, owner_id, "654321")
    assert locked.value.code == "demo_mpin_locked"


def test_demo_mpin_reset_removes_existing_secret_and_unlocks_creation() -> None:
    repository = FakeSecurityRepository()
    owner_id = str(uuid4())
    set_demo_mpin(repository, owner_id, pin="123456")

    reset = reset_demo_mpin(repository, owner_id)

    assert reset["pin_hash"] is None
    assert reset["failed_attempts"] == 0
    assert reset["locked"] is False
    assert not repository.records[(owner_id, owner_id)]["pin_hash"]
