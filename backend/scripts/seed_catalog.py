"""Explicit development command for the canonical SpendShield taxonomy."""

from __future__ import annotations

from app.core.config import get_settings
from app.db.manager import DatabaseManager
from app.repositories.categories import MongoCategoryRepository
from app.seed.catalog import seed_default_categories


def main() -> None:
    """Seed canonical categories without creating merchants implicitly."""

    settings = get_settings()
    manager = DatabaseManager(settings)
    try:
        categories = seed_default_categories(MongoCategoryRepository(manager))
        print(f"Seeded {len(categories)} canonical category pairs.")
    finally:
        manager.close()


if __name__ == "__main__":
    main()
