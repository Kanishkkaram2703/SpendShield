"""Live MongoDB-rs0 coverage for the read-only analytics boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.test_merchants_api import (
    ADMIN_EMAIL,
    PASSWORD,
    catalog_api,
    create_merchant,
    login,
    register_user,
)


def create_account(client, headers: dict[str, str]) -> str:
    response = client.post("/api/v1/accounts", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["account_id"]


def create_payment(
    client,
    headers: dict[str, str],
    *,
    account_id: str,
    merchant_id: str,
    amount: str,
    key: str,
) -> dict:
    response = client.post(
        "/api/v1/payments",
        headers={**headers, "Idempotency-Key": key},
        json={
            "account_id": account_id,
            "amount": amount,
            "currency": "INR",
            "merchant_id": merchant_id,
            "transaction_channel": "QR_SIMULATED",
            "demo_mpin": "123456",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["transaction"]


def analytics_range() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "start_at": (now - timedelta(days=1)).isoformat(),
        "end_at": (now + timedelta(days=1)).isoformat(),
    }


def test_analytics_is_owner_scoped_and_uses_completed_snapshot_data(catalog_api) -> None:
    client, users, _, _ = catalog_api
    admin_headers = login(client, ADMIN_EMAIL)
    user_headers = register_user(client, "analytics-owner@example.com")
    other_headers = register_user(client, "analytics-other@example.com")
    owner_account = create_account(client, user_headers)
    other_account = create_account(client, other_headers)

    food = create_merchant(client, admin_headers, name="Analytics Cafe")
    travel = create_merchant(
        client,
        admin_headers,
        name="Analytics Metro",
        category_id="transport",
        subcategory_id="public_transit",
    )
    create_payment(
        client,
        user_headers,
        account_id=owner_account,
        merchant_id=food["merchant_id"],
        amount="25.00",
        key="analytics-food",
    )
    create_payment(
        client,
        user_headers,
        account_id=owner_account,
        merchant_id=travel["merchant_id"],
        amount="10.00",
        key="analytics-travel",
    )
    create_payment(
        client,
        other_headers,
        account_id=other_account,
        merchant_id=food["merchant_id"],
        amount="900.00",
        key="analytics-other",
    )

    params = analytics_range()
    summary = client.get(
        "/api/v1/analytics/spending/summary",
        headers=user_headers,
        params=params,
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["currency"] == "INR"
    assert body["total_spending"] == "35.00"
    assert body["transaction_count"] == 2
    assert body["average_transaction"] == "17.50"
    assert body["largest_payment_amount"] == "25.00"
    assert body["current_balance"] == "9965.00"
    assert body["calculation_basis"] == "completed_mongodb_transactions"

    categories = client.get(
        "/api/v1/analytics/spending/categories",
        headers=user_headers,
        params=params,
    )
    assert categories.status_code == 200, categories.text
    category_items = categories.json()["categories"]
    assert {item["category_id"] for item in category_items} == {
        "food",
        "transport",
    }
    assert sum(float(item["share_percent"]) for item in category_items) == 100.0

    merchants = client.get(
        "/api/v1/analytics/spending/merchants",
        headers=user_headers,
        params=params,
    )
    assert merchants.status_code == 200, merchants.text
    merchant_items = merchants.json()["merchants"]
    assert merchant_items[0]["merchant_name"] == "Analytics Cafe"
    assert merchant_items[0]["total_spending"] == "25.00"
    assert {item["merchant_id"] for item in merchant_items} == {
        food["merchant_id"],
        travel["merchant_id"],
    }

    trends = client.get(
        "/api/v1/analytics/spending/trends",
        headers=user_headers,
        params={**params, "interval": "daily"},
    )
    assert trends.status_code == 200, trends.text
    assert sum(item["transaction_count"] for item in trends.json()["trends"]) == 2
    assert sum(
        float(item["total_spending"]) for item in trends.json()["trends"]
    ) == 35.0

    for interval in ("weekly", "monthly"):
        bucketed = client.get(
            "/api/v1/analytics/spending/trends",
            headers=user_headers,
            params={**params, "interval": interval},
        )
        assert bucketed.status_code == 200, bucketed.text
        assert sum(
            float(item["total_spending"])
            for item in bucketed.json()["trends"]
        ) == 35.0

    largest = client.get(
        "/api/v1/analytics/spending/largest",
        headers=user_headers,
        params={**params, "limit": 1},
    )
    assert largest.status_code == 200, largest.text
    assert largest.json()["payments"][0]["amount"] == "25.00"

    # The other user's ₹900 payment must not leak into the owner-scoped total.
    assert body["total_spending"] != "935.00"
    assert users.get_by_email("analytics-owner@example.com") is not None


def test_analytics_excludes_rejected_transactions_and_validates_ranges(catalog_api) -> None:
    client, _, _, _ = catalog_api
    admin_headers = login(client, ADMIN_EMAIL)
    user_headers = register_user(client, "analytics-validation@example.com")
    account_id = create_account(client, user_headers)
    merchant = create_merchant(client, admin_headers, name="Validation Cafe")
    create_payment(
        client,
        user_headers,
        account_id=account_id,
        merchant_id=merchant["merchant_id"],
        amount="10.00",
        key="analytics-valid",
    )
    rejected = client.post(
        "/api/v1/payments",
        headers={**user_headers, "Idempotency-Key": "analytics-rejected"},
        json={
            "account_id": account_id,
            "amount": "999999.00",
            "currency": "INR",
            "merchant_id": merchant["merchant_id"],
            "transaction_channel": "QR_SIMULATED",
            "demo_mpin": "123456",
        },
    )
    assert rejected.status_code == 409

    params = analytics_range()
    summary = client.get(
        "/api/v1/analytics/spending/summary",
        headers=user_headers,
        params=params,
    )
    assert summary.status_code == 200
    assert summary.json()["total_spending"] == "10.00"
    assert summary.json()["transaction_count"] == 1

    empty = client.get(
        "/api/v1/analytics/spending/summary",
        headers=user_headers,
        params={
            "start_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "end_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        },
    )
    assert empty.status_code == 200
    assert empty.json()["total_spending"] == "0.00"
    assert empty.json()["transaction_count"] == 0

    invalid_order = client.get(
        "/api/v1/analytics/spending/summary",
        headers=user_headers,
        params={"start_at": params["end_at"], "end_at": params["start_at"]},
    )
    assert invalid_order.status_code == 422
    assert invalid_order.json()["error"]["code"] == "invalid_analytics_period"

    too_long = client.get(
        "/api/v1/analytics/spending/summary",
        headers=user_headers,
        params={
            "start_at": (datetime.now(timezone.utc) - timedelta(days=367)).isoformat(),
            "end_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert too_long.status_code == 422

    too_many = client.get(
        "/api/v1/analytics/spending/merchants",
        headers=user_headers,
        params={**params, "limit": 101},
    )
    assert too_many.status_code == 422


def test_analytics_requires_authentication_and_missing_account_is_safe(client) -> None:
    unauthorized = client.get("/api/v1/analytics/spending/summary")
    assert unauthorized.status_code == 401


__all__ = []
