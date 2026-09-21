"""Deterministic system-category seed data.

This module is invoked explicitly by development tooling or tests.  The
application startup path never inserts seed data implicitly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.catalog import CategoryRecord
from app.repositories.categories import CategoryRepository

CATALOG_SEED_TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _category(
    category_id: str,
    category_name: str,
    subcategory_id: str,
    subcategory_name: str,
) -> CategoryRecord:
    return CategoryRecord(
        category_id=category_id,
        category_name=category_name,
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        is_active=True,
        created_at=CATALOG_SEED_TIMESTAMP,
        updated_at=CATALOG_SEED_TIMESTAMP,
    )


DEFAULT_CATEGORIES: tuple[CategoryRecord, ...] = (
    _category("bills", "Bills", "insurance", "Insurance"),
    _category("bills", "Bills", "telecom", "Telecom"),
    _category("bills", "Bills", "utilities", "Utilities"),
    _category("education", "Education", "courses", "Courses"),
    _category("entertainment", "Entertainment", "events", "Events"),
    _category("entertainment", "Entertainment", "streaming", "Streaming"),
    _category("food", "Food", "cafes", "Cafes"),
    _category("food", "Food", "restaurants", "Restaurants"),
    _category("grocery", "Grocery", "general", "General"),
    _category("grocery", "Grocery", "supermarkets", "Supermarkets"),
    _category("healthcare", "Healthcare", "medical", "Medical"),
    _category("other", "Other", "general", "General"),
    _category("shopping", "Shopping", "clothing", "Clothing"),
    _category("shopping", "Shopping", "electronics", "Electronics"),
    _category("shopping", "Shopping", "general", "General"),
    _category("subscriptions", "Subscriptions", "digital_services", "Digital Services"),
    _category("transport", "Transport", "fuel", "Fuel"),
    _category("transport", "Transport", "public_transit", "Public Transit"),
    _category("transport", "Transport", "taxi", "Taxi"),
)


def seed_default_categories(repository: CategoryRepository) -> tuple[CategoryRecord, ...]:
    """Ensure the small canonical taxonomy exists and return persisted rows."""

    return tuple(repository.ensure(category) for category in DEFAULT_CATEGORIES)


__all__ = [
    "CATALOG_SEED_TIMESTAMP",
    "DEFAULT_CATEGORIES",
    "seed_default_categories",
]
