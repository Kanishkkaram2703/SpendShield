"""Owner-scoped demo MPIN state and verification."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.repositories.demo_resources import DemoResourceRepository


MAX_FAILED_ATTEMPTS = 5


def require_demo_mpin(repository: Any | None, user_id: str, pin: str | None) -> None:
    """Require the owner-scoped demo MPIN for a sensitive fictional operation.

    Dependency-free unit applications may intentionally omit the Mongo-backed
    demo-security adapter; those adapters exercise financial rules without a
    persistence boundary. The configured application always supplies the
    repository and therefore enforces this check.
    """

    if repository is None:
        return
    if pin is None:
        raise AppError(
            code="demo_mpin_required",
            message="Enter the six-digit demo MPIN to continue.",
            status_code=422,
        )
    verify_demo_mpin(repository, user_id, pin)


def security_status(repository: DemoResourceRepository, user_id: str) -> dict[str, Any]:
    record = repository.get(user_id, user_id)
    return {
        "configured": bool(record and record.get("pin_hash")),
        "locked": bool(record and record.get("locked", False)),
        "failed_attempts": int(record.get("failed_attempts", 0)) if record else 0,
    }


def set_demo_mpin(
    repository: DemoResourceRepository,
    user_id: str,
    *,
    pin: str,
    current_pin: str | None = None,
) -> dict[str, Any]:
    record = repository.get(user_id, user_id)
    if record and record.get("locked"):
        raise AppError(code="demo_mpin_locked", message="The demo MPIN is locked. Reset it through the demo recovery flow.", status_code=423)
    if record and record.get("pin_hash"):
        if not current_pin or not verify_password(current_pin, str(record["pin_hash"])):
            raise AppError(code="demo_mpin_current_invalid", message="The current demo MPIN is incorrect.", status_code=401)
    values = {
        "user_id": user_id,
        "pin_hash": hash_password(pin),
        "failed_attempts": 0,
        "locked": False,
        "demo_only": True,
    }
    if record:
        updated = repository.update(user_id, user_id, values)
        assert updated is not None
        return updated
    return repository.create(user_id, values)


def reset_demo_mpin(repository: DemoResourceRepository, user_id: str) -> dict[str, Any]:
    """Remove the configured demo MPIN while retaining a clean security record."""

    values = {
        "user_id": user_id,
        "pin_hash": None,
        "failed_attempts": 0,
        "locked": False,
        "demo_only": True,
    }
    record = repository.get(user_id, user_id)
    if record:
        updated = repository.update(user_id, user_id, values)
        assert updated is not None
        return updated
    return repository.create(user_id, values)


def verify_demo_mpin(repository: DemoResourceRepository, user_id: str, pin: str) -> None:
    record = repository.get(user_id, user_id)
    if not record or not record.get("pin_hash"):
        raise AppError(code="demo_mpin_not_configured", message="Set a demo MPIN before making this protected demo payment.", status_code=409)
    if record.get("locked"):
        raise AppError(code="demo_mpin_locked", message="The demo MPIN is locked after repeated failures.", status_code=423)
    if verify_password(pin, str(record["pin_hash"])):
        if record.get("failed_attempts"):
            repository.update(user_id, user_id, {"failed_attempts": 0})
        return
    attempts = int(record.get("failed_attempts", 0)) + 1
    repository.update(user_id, user_id, {"failed_attempts": attempts, "locked": attempts >= MAX_FAILED_ATTEMPTS})
    raise AppError(
        code="demo_mpin_invalid",
        message="The demo MPIN is incorrect.",
        status_code=401,
        details={"attempts_remaining": max(0, MAX_FAILED_ATTEMPTS - attempts)},
    )


__all__ = ["require_demo_mpin", "reset_demo_mpin", "security_status", "set_demo_mpin", "verify_demo_mpin"]
