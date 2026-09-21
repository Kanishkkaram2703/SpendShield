"""MongoDB collection and index definitions for the operational store."""

from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

MONGO_COLLECTIONS = (
    "users",
    "accounts",
    "categories",
    "merchants",
    "demo_merchants",
    "transactions",
    "subscriptions",
    "cases",
    "evidence",
    "findings",
    "audit_records",
    "cards",
    "billers",
    "contacts",
    "beneficiaries",
    "notifications",
    "demo_security",
)

MONGO_INDEXES: dict[str, tuple[IndexModel, ...]] = {
    "users": (
        IndexModel([("user_id", ASCENDING)], unique=True, name="uq_users_user_id"),
        IndexModel([("email", ASCENDING)], unique=True, name="uq_users_email"),
    ),
    "accounts": (
        IndexModel([("account_id", ASCENDING)], unique=True, name="uq_accounts_id"),
        IndexModel(
            [("user_id", ASCENDING)],
            # Keep the historical index name for compatibility; uniqueness is
            # intentionally removed to support multiple demo accounts.
            name="uq_accounts_user_id",
        ),
    ),
    "categories": (
        IndexModel(
            [("category_id", ASCENDING), ("subcategory_id", ASCENDING)],
            unique=True,
            name="uq_categories_pair",
        ),
        IndexModel(
            [("is_active", ASCENDING), ("category_id", ASCENDING)],
            name="ix_categories_active",
        ),
    ),
    "merchants": (
        IndexModel(
            [("merchant_id", ASCENDING)], unique=True, name="uq_merchants_id"
        ),
        IndexModel([("status", ASCENDING)], name="ix_merchants_status"),
        IndexModel(
            [("status", ASCENDING), ("merchant_name_key", ASCENDING), ("merchant_id", ASCENDING)],
            name="ix_merchants_listing",
        ),
        IndexModel(
            [
                ("category_id", ASCENDING),
                ("subcategory_id", ASCENDING),
                ("status", ASCENDING),
            ],
            name="ix_merchants_category_status",
        ),
    ),
    "demo_merchants": (
        IndexModel([("merchant_id", ASCENDING)], unique=True, name="uq_demo_merchants_id"),
        IndexModel([("status", ASCENDING), ("merchant_name_key", ASCENDING)], name="ix_demo_merchants_listing"),
    ),
    "transactions": (
        IndexModel(
            [("transaction_id", ASCENDING)],
            unique=True,
            name="uq_transactions_id",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            name="ix_transactions_user_time",
        ),
        IndexModel(
            [
                ("user_id", ASCENDING),
                ("timestamp", DESCENDING),
                ("transaction_id", DESCENDING),
            ],
            name="ix_transactions_user_time_id",
        ),
        IndexModel(
            [
                ("user_id", ASCENDING),
                ("status", ASCENDING),
                ("currency", ASCENDING),
                ("timestamp", DESCENDING),
            ],
            name="ix_transactions_analytics",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("idempotency_key", ASCENDING)],
            unique=True,
            name="uq_transactions_user_idempotency",
        ),
        IndexModel(
            [("account_id", ASCENDING), ("timestamp", DESCENDING)],
            name="ix_transactions_account_time",
        ),
        IndexModel(
            [("merchant_id", ASCENDING), ("timestamp", DESCENDING)],
            name="ix_transactions_merchant_time",
        ),
    ),
    "subscriptions": (
        IndexModel(
            [("subscription_id", ASCENDING)],
            unique=True,
            name="uq_subscriptions_id",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("next_payment_date", ASCENDING)],
            name="ix_subscriptions_user_next_payment",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("idempotency_key", ASCENDING)],
            unique=True,
            sparse=True,
            name="uq_subscriptions_user_idempotency",
        ),
    ),
    "cases": (
        IndexModel([("case_id", ASCENDING)], unique=True, name="uq_cases_id"),
        IndexModel(
            [("status", ASCENDING), ("created_at", DESCENDING)],
            name="ix_cases_status_created",
        ),
    ),
    "evidence": (
        IndexModel([("evidence_id", ASCENDING)], unique=True, name="uq_evidence_id"),
        IndexModel([("case_id", ASCENDING)], name="ix_evidence_case_id"),
        IndexModel([("sha256", ASCENDING)], name="ix_evidence_sha256"),
    ),
    "findings": (
        IndexModel([("finding_id", ASCENDING)], unique=True, name="uq_findings_id"),
        IndexModel(
            [("case_id", ASCENDING), ("created_at", DESCENDING)],
            name="ix_findings_case_created",
        ),
    ),
    "audit_records": (
        IndexModel(
            [("audit_id", ASCENDING)], unique=True, name="uq_audit_records_id"
        ),
        IndexModel(
            [("actor_id", ASCENDING), ("timestamp", DESCENDING)],
            name="ix_audit_actor_time",
        ),
        IndexModel(
            [("case_id", ASCENDING), ("timestamp", DESCENDING)],
            name="ix_audit_case_time",
        ),
        IndexModel(
            [("publication_status", ASCENDING), ("publication_next_attempt_at", ASCENDING)],
            name="ix_audit_publication_due",
        ),
    ),
    "cards": (
        IndexModel([("card_id", ASCENDING)], unique=True, name="uq_cards_id"),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_cards_user_time"),
    ),
    "billers": (
        IndexModel([("biller_id", ASCENDING)], unique=True, name="uq_billers_id"),
        IndexModel([("user_id", ASCENDING), ("category", ASCENDING), ("identifier", ASCENDING)], unique=True, name="uq_billers_owner_identifier"),
    ),
    "contacts": (
        IndexModel([("contact_id", ASCENDING)], unique=True, name="uq_contacts_id"),
        IndexModel([("user_id", ASCENDING), ("phone", ASCENDING)], unique=True, name="uq_contacts_owner_phone"),
        IndexModel([("user_id", ASCENDING), ("favorite", DESCENDING), ("name_key", ASCENDING)], name="ix_contacts_listing"),
    ),
    "beneficiaries": (
        IndexModel([("beneficiary_id", ASCENDING)], unique=True, name="uq_beneficiaries_id"),
        IndexModel([("user_id", ASCENDING), ("account_number", ASCENDING), ("bank_code", ASCENDING)], unique=True, name="uq_beneficiaries_owner_account"),
        IndexModel([("user_id", ASCENDING), ("favorite", DESCENDING), ("name_key", ASCENDING)], name="ix_beneficiaries_listing"),
    ),
    "notifications": (
        IndexModel([("notification_id", ASCENDING)], unique=True, name="uq_notifications_id"),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_notifications_user_time"),
        IndexModel([("user_id", ASCENDING), ("source_transaction_id", ASCENDING)], unique=True, sparse=True, name="uq_notifications_source_transaction"),
    ),
    "demo_security": (
        IndexModel([("user_id", ASCENDING)], unique=True, name="uq_demo_security_user"),
    ),
}


def ensure_mongo_schema(database: Any) -> dict[str, int]:
    """Create required collections and deliberate indexes idempotently."""

    existing = set(database.list_collection_names())
    created_collections = 0
    created_indexes = 0

    for collection_name in MONGO_COLLECTIONS:
        if collection_name not in existing:
            database.create_collection(collection_name)
            created_collections += 1
        if collection_name == "accounts":
            # The original foundation used one unique owner index.  This
            # additive migration removes only that obsolete index so multiple
            # fictional accounts can coexist; account documents are kept.
            account_indexes = database[collection_name].index_information()
            if account_indexes.get("uq_accounts_user_id", {}).get("unique"):
                database[collection_name].drop_index("uq_accounts_user_id")
                account_indexes = database[collection_name].index_information()
            # A previously validated SpendShield database used the same
            # non-unique key pattern under the legacy ``ix_accounts_user_id``
            # name.  MongoDB treats an index-name mismatch as an
            # IndexOptionsConflict even when the key pattern and uniqueness
            # are otherwise compatible.  Rename it by dropping only that
            # obsolete index definition; account documents are never touched.
            legacy_owner_index = account_indexes.get("ix_accounts_user_id")
            if legacy_owner_index and not account_indexes.get("uq_accounts_user_id"):
                database[collection_name].drop_index("ix_accounts_user_id")
        indexes = MONGO_INDEXES.get(collection_name, ())
        if indexes:
            database[collection_name].create_indexes(list(indexes))
            created_indexes += len(indexes)

    return {
        "collections": len(MONGO_COLLECTIONS),
        "created_collections": created_collections,
        "indexes_applied": created_indexes,
    }


__all__ = ["MONGO_COLLECTIONS", "MONGO_INDEXES", "ensure_mongo_schema"]
