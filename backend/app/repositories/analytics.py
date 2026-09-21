"""Read-only analytics repository over MongoDB current transaction state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from bson.decimal128 import Decimal128
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager
from app.domain.analytics import (
    AnalyticsInterval,
    AnalyticsPeriod,
    CategorySpending,
    LargestPayment,
    MerchantSpending,
    SpendingSummary,
    SpendingTrend,
    money,
    utc_datetime,
)
from app.domain.financial import TransactionStatus


@runtime_checkable
class AnalyticsRepository(Protocol):
    """Persistence contract for owner-scoped, non-mutating analytics reads."""

    def spending_summary(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
    ) -> SpendingSummary:
        """Aggregate completed spending for one owner and period."""

    def category_breakdown(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        limit: int = 100,
    ) -> tuple[CategorySpending, ...]:
        """Group completed spending by immutable category snapshots."""

    def merchant_breakdown(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        limit: int = 100,
    ) -> tuple[MerchantSpending, ...]:
        """Group completed spending by persisted merchant identity/snapshot."""

    def trends(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        interval: AnalyticsInterval,
    ) -> tuple[SpendingTrend, ...]:
        """Aggregate completed spending into UTC calendar buckets."""

    def largest_payments(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        limit: int = 10,
    ) -> tuple[LargestPayment, ...]:
        """Return a bounded largest-payment projection."""


class UnavailableAnalyticsRepository:
    """Explicit adapter when MongoDB is not configured or available."""

    def _unavailable(self) -> None:
        raise DatabaseUnavailableError()

    def spending_summary(self, *_: Any, **__: Any) -> SpendingSummary:
        self._unavailable()
        raise AssertionError("unreachable")

    def category_breakdown(self, *_: Any, **__: Any) -> tuple[CategorySpending, ...]:
        self._unavailable()
        raise AssertionError("unreachable")

    def merchant_breakdown(self, *_: Any, **__: Any) -> tuple[MerchantSpending, ...]:
        self._unavailable()
        raise AssertionError("unreachable")

    def trends(self, *_: Any, **__: Any) -> tuple[SpendingTrend, ...]:
        self._unavailable()
        raise AssertionError("unreachable")

    def largest_payments(self, *_: Any, **__: Any) -> tuple[LargestPayment, ...]:
        self._unavailable()
        raise AssertionError("unreachable")


class MongoAnalyticsRepository:
    """Read MongoDB's current transaction state without changing it.

    Analytics deliberately use only ``COMPLETED`` transaction documents.  The
    repository never reads Cassandra and never reconstructs account state from
    events.  Category and merchant labels come from payment-time snapshots;
    current catalog state is not joined into historical totals.
    """

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal128):
            return value.to_decimal()
        return Decimal(str(value))

    @staticmethod
    def _mongo_datetime(value: datetime) -> datetime:
        normalized = utc_datetime(value)
        return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["transactions"]

    @staticmethod
    def _validate_limit(limit: int, *, maximum: int = 100) -> None:
        if limit < 1 or limit > maximum:
            raise ValueError(f"limit must be between 1 and {maximum}")

    def _match(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
    ) -> dict[str, Any]:
        return {
            "user_id": owner_id,
            "currency": currency,
            "status": TransactionStatus.COMPLETED.value,
            "timestamp": {
                "$gte": self._mongo_datetime(period.start_at),
                "$lt": self._mongo_datetime(period.end_at),
            },
        }

    def _aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            return list(self._collection().aggregate(pipeline, allowDiskUse=False))
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def spending_summary(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
    ) -> SpendingSummary:
        match = self._match(owner_id, currency=currency, period=period)
        rows = self._aggregate(
            [
                {"$match": match},
                {
                    "$group": {
                        "_id": None,
                        "total_spending": {"$sum": "$amount"},
                        "transaction_count": {"$sum": 1},
                    }
                },
            ]
        )
        row = rows[0] if rows else None
        total = money(self._decimal(row["total_spending"]) if row else 0)
        count = int(row["transaction_count"]) if row else 0
        average = money(total / count) if count else money(0)

        try:
            largest = self._collection().find_one(
                match,
                {
                    "transaction_id": 1,
                    "amount": 1,
                },
                sort=[
                    ("amount", DESCENDING),
                    ("timestamp", DESCENDING),
                    ("transaction_id", DESCENDING),
                ],
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return SpendingSummary(
            total_spending=total,
            transaction_count=count,
            average_transaction=average,
            largest_payment_amount=(
                money(self._decimal(largest["amount"])) if largest else None
            ),
            largest_transaction_id=(
                str(largest["transaction_id"]) if largest else None
            ),
        )

    def category_breakdown(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        limit: int = 100,
    ) -> tuple[CategorySpending, ...]:
        self._validate_limit(limit)
        rows = self._aggregate(
            [
                {"$match": self._match(owner_id, currency=currency, period=period)},
                {
                    "$group": {
                        "_id": {
                            "category_id": "$category_id",
                            "category_name": "$category_name",
                            "subcategory_id": "$subcategory_id",
                            "subcategory_name": "$subcategory_name",
                        },
                        "total_spending": {"$sum": "$amount"},
                        "transaction_count": {"$sum": 1},
                    }
                },
            ]
        )
        rows.sort(
            key=lambda row: (
                -self._decimal(row["total_spending"]),
                str(row["_id"].get("category_id") or ""),
                str(row["_id"].get("subcategory_id") or ""),
            )
        )
        return tuple(
            CategorySpending(
                category_id=row["_id"].get("category_id"),
                category_name=row["_id"].get("category_name"),
                subcategory_id=row["_id"].get("subcategory_id"),
                subcategory_name=row["_id"].get("subcategory_name"),
                total_spending=money(self._decimal(row["total_spending"])),
                transaction_count=int(row["transaction_count"]),
            )
            for row in rows[:limit]
        )

    def merchant_breakdown(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        limit: int = 100,
    ) -> tuple[MerchantSpending, ...]:
        self._validate_limit(limit)
        rows = self._aggregate(
            [
                {"$match": self._match(owner_id, currency=currency, period=period)},
                {
                    "$group": {
                        "_id": {
                            "merchant_id": "$merchant_id",
                            "merchant_name": "$merchant_name",
                        },
                        "total_spending": {"$sum": "$amount"},
                        "transaction_count": {"$sum": 1},
                    }
                },
            ]
        )
        rows.sort(
            key=lambda row: (
                -self._decimal(row["total_spending"]),
                str(row["_id"].get("merchant_id") or ""),
            )
        )
        return tuple(
            MerchantSpending(
                merchant_id=row["_id"].get("merchant_id"),
                merchant_name=row["_id"].get("merchant_name"),
                total_spending=money(self._decimal(row["total_spending"])),
                transaction_count=int(row["transaction_count"]),
            )
            for row in rows[:limit]
        )

    def trends(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        interval: AnalyticsInterval,
    ) -> tuple[SpendingTrend, ...]:
        date_trunc: dict[str, Any] = {
            "date": "$timestamp",
            "unit": {
                AnalyticsInterval.DAILY: "day",
                AnalyticsInterval.WEEKLY: "week",
                AnalyticsInterval.MONTHLY: "month",
            }[interval],
            "binSize": 1,
            "timezone": "UTC",
        }
        if interval is AnalyticsInterval.WEEKLY:
            date_trunc["startOfWeek"] = "monday"
        rows = self._aggregate(
            [
                {"$match": self._match(owner_id, currency=currency, period=period)},
                {
                    "$group": {
                        "_id": {"$dateTrunc": date_trunc},
                        "total_spending": {"$sum": "$amount"},
                        "transaction_count": {"$sum": 1},
                    }
                },
            ]
        )
        rows.sort(key=lambda row: row["_id"])
        result: list[SpendingTrend] = []
        for row in rows:
            start = utc_datetime(row["_id"])
            if interval is AnalyticsInterval.DAILY:
                end = start + timedelta(days=1)
            elif interval is AnalyticsInterval.WEEKLY:
                end = start + timedelta(days=7)
            else:
                month = start.month + 1
                year = start.year
                if month == 13:
                    month = 1
                    year += 1
                end = start.replace(year=year, month=month)
            result.append(
                SpendingTrend(
                    period_start=start,
                    period_end=end,
                    total_spending=money(self._decimal(row["total_spending"])),
                    transaction_count=int(row["transaction_count"]),
                )
            )
        return tuple(result)

    def largest_payments(
        self,
        owner_id: str,
        *,
        currency: str,
        period: AnalyticsPeriod,
        limit: int = 10,
    ) -> tuple[LargestPayment, ...]:
        self._validate_limit(limit)
        try:
            documents = list(
                self._collection()
                .find(
                    self._match(owner_id, currency=currency, period=period),
                    {
                        "transaction_id": 1,
                        "amount": 1,
                        "currency": 1,
                        "merchant_id": 1,
                        "merchant_name": 1,
                        "category_id": 1,
                        "category_name": 1,
                        "subcategory_id": 1,
                        "subcategory_name": 1,
                        "timestamp": 1,
                    },
                )
                .sort(
                    [
                        ("amount", DESCENDING),
                        ("timestamp", DESCENDING),
                        ("transaction_id", DESCENDING),
                    ]
                )
                .limit(limit)
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return tuple(
            LargestPayment(
                transaction_id=str(document["transaction_id"]),
                amount=money(self._decimal(document["amount"])),
                currency=str(document["currency"]),
                merchant_id=document.get("merchant_id"),
                merchant_name=document.get("merchant_name"),
                category_id=document.get("category_id"),
                category_name=document.get("category_name"),
                subcategory_id=document.get("subcategory_id"),
                subcategory_name=document.get("subcategory_name"),
                occurred_at=utc_datetime(document["timestamp"]),
            )
            for document in documents
        )


__all__ = [
    "AnalyticsRepository",
    "MongoAnalyticsRepository",
    "UnavailableAnalyticsRepository",
]
