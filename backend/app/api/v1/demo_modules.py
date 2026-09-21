"""Authenticated fictional contacts, billers, cards, and notifications."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.dependencies import (
    get_beneficiaries_repository,
    get_billers_repository,
    get_cards_repository,
    get_contacts_repository,
    get_current_user,
    get_notifications_repository,
    get_optional_demo_security_repository,
)
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.services.demo_security_service import require_demo_mpin
from app.repositories.demo_resources import (
    DemoResourceRepository,
    DuplicateDemoResourceError,
)
from app.repositories.users import UserRecord
from app.schemas.demo_modules import (
    BeneficiaryCreateRequest,
    BeneficiaryListResponse,
    BeneficiaryResponse,
    BeneficiaryUpdateRequest,
    BillerCreateRequest,
    BillerListResponse,
    BillerResponse,
    BillerUpdateRequest,
    CardListResponse,
    CardLimitRequest,
    CardPinRequest,
    CardResponse,
    CardStatusRequest,
    ContactCreateRequest,
    ContactListResponse,
    ContactResponse,
    ContactUpdateRequest,
    NotificationListResponse,
    NotificationResponse,
)

router = APIRouter(tags=["demo-modules"])


def _not_found(code: str, label: str) -> AppError:
    return AppError(code=code, message=f"{label} was not found.", status_code=404)


def _duplicate(label: str) -> AppError:
    return AppError(
        code="duplicate_demo_resource",
        message=f"That {label} already exists for this demo user.",
        status_code=409,
    )


def _contact(document: dict) -> ContactResponse:
    return ContactResponse(
        contact_id=str(document["contact_id"]),
        name=str(document["name"]),
        phone=str(document["phone"]),
        email=document.get("email"),
        favorite=bool(document.get("favorite", False)),
        contact_type=document.get("contact_type", "PERSON"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _beneficiary(document: dict) -> BeneficiaryResponse:
    return BeneficiaryResponse(
        beneficiary_id=str(document["beneficiary_id"]),
        name=str(document["name"]),
        account_number=str(document["account_number"]),
        bank_name=str(document["bank_name"]),
        bank_code=str(document["bank_code"]),
        note=document.get("note"),
        favorite=bool(document.get("favorite", False)),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _biller(document: dict) -> BillerResponse:
    return BillerResponse(
        biller_id=str(document["biller_id"]),
        category=document["category"],
        provider=document["provider"],
        identifier=document["identifier"],
        nickname=document.get("nickname"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _card(document: dict) -> CardResponse:
    return CardResponse(
        card_id=str(document["card_id"]),
        holder_name=str(document["holder_name"]),
        masked_card_number=str(document["masked_card_number"]),
        expiry=str(document["expiry"]),
        masked_cvv="***",
        status=document.get("status", "ACTIVE"),
        spending_limit=document["spending_limit"],
        currency=document["currency"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _notification(document: dict) -> NotificationResponse:
    return NotificationResponse(
        notification_id=str(document["notification_id"]),
        category=str(document["category"]),
        title=str(document["title"]),
        message=str(document["message"]),
        is_read=bool(document.get("is_read", False)),
        created_at=document["created_at"],
    )


def _create_notification(
    repository: DemoResourceRepository,
    user_id: str,
    *,
    notification_id: str,
    category: str,
    title: str,
    message: str,
) -> None:
    try:
        repository.create(
            user_id,
            {
                "notification_id": notification_id,
                "category": category,
                "title": title,
                "message": message,
                "is_read": False,
            },
        )
    except DuplicateDemoResourceError:
        return


@router.get("/contacts", response_model=ContactListResponse)
def list_contacts(
    search: str | None = Query(default=None, max_length=128),
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_contacts_repository),
) -> ContactListResponse:
    contacts = repository.list(user.user_id)
    query = search.strip().casefold() if search else None
    if query:
        contacts = tuple(item for item in contacts if query in str(item.get("name", "")).casefold() or query in str(item.get("phone", "")).casefold())
    return ContactListResponse(contacts=[_contact(item) for item in contacts])


@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_contacts_repository),
) -> ContactResponse:
    try:
        return _contact(repository.create(user.user_id, payload.model_dump()))
    except DuplicateDemoResourceError as exc:
        raise _duplicate("contact") from exc


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID,
    payload: ContactUpdateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_contacts_repository),
) -> ContactResponse:
    document = repository.update(user.user_id, str(contact_id), payload.model_dump())
    if document is None:
        raise _not_found("contact_not_found", "Contact")
    return _contact(document)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: UUID,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_contacts_repository),
) -> None:
    if not repository.delete(user.user_id, str(contact_id)):
        raise _not_found("contact_not_found", "Contact")


@router.get("/beneficiaries", response_model=BeneficiaryListResponse)
def list_beneficiaries(
    search: str | None = Query(default=None, max_length=128),
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_beneficiaries_repository),
) -> BeneficiaryListResponse:
    items = repository.list(user.user_id)
    query = search.strip().casefold() if search else None
    if query:
        items = tuple(item for item in items if query in str(item.get("name", "")).casefold() or query in str(item.get("account_number", "")).casefold())
    return BeneficiaryListResponse(beneficiaries=[_beneficiary(item) for item in items])


@router.post("/beneficiaries", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
def create_beneficiary(
    payload: BeneficiaryCreateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_beneficiaries_repository),
    notifications: DemoResourceRepository = Depends(get_notifications_repository),
) -> BeneficiaryResponse:
    try:
        document = repository.create(user.user_id, payload.model_dump())
        _create_notification(notifications, user.user_id, notification_id=f"beneficiary-{document['beneficiary_id']}", category="BENEFICIARY", title="Demo beneficiary added", message=f"{document['name']} was added to your demo beneficiaries.")
        return _beneficiary(document)
    except DuplicateDemoResourceError as exc:
        raise _duplicate("beneficiary") from exc


@router.patch("/beneficiaries/{beneficiary_id}", response_model=BeneficiaryResponse)
def update_beneficiary(
    beneficiary_id: UUID,
    payload: BeneficiaryUpdateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_beneficiaries_repository),
) -> BeneficiaryResponse:
    document = repository.update(user.user_id, str(beneficiary_id), payload.model_dump())
    if document is None:
        raise _not_found("beneficiary_not_found", "Beneficiary")
    return _beneficiary(document)


@router.delete("/beneficiaries/{beneficiary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_beneficiary(
    beneficiary_id: UUID,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_beneficiaries_repository),
) -> None:
    if not repository.delete(user.user_id, str(beneficiary_id)):
        raise _not_found("beneficiary_not_found", "Beneficiary")


@router.get("/billers", response_model=BillerListResponse)
def list_billers(
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_billers_repository),
) -> BillerListResponse:
    return BillerListResponse(billers=[_biller(item) for item in repository.list(user.user_id)])


@router.post("/billers", response_model=BillerResponse, status_code=status.HTTP_201_CREATED)
def create_biller(
    payload: BillerCreateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_billers_repository),
) -> BillerResponse:
    try:
        return _biller(repository.create(user.user_id, payload.model_dump()))
    except DuplicateDemoResourceError as exc:
        raise _duplicate("biller") from exc


@router.patch("/billers/{biller_id}", response_model=BillerResponse)
def update_biller(
    biller_id: UUID,
    payload: BillerUpdateRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_billers_repository),
) -> BillerResponse:
    document = repository.update(user.user_id, str(biller_id), payload.model_dump())
    if document is None:
        raise _not_found("biller_not_found", "Biller")
    return _biller(document)


@router.delete("/billers/{biller_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_biller(
    biller_id: UUID,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_billers_repository),
) -> None:
    if not repository.delete(user.user_id, str(biller_id)):
        raise _not_found("biller_not_found", "Biller")


@router.get("/cards", response_model=CardListResponse)
def list_cards(
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_cards_repository),
) -> CardListResponse:
    return CardListResponse(cards=[_card(item) for item in repository.list(user.user_id)])


@router.post("/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_card(
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_cards_repository),
) -> CardResponse:
    card = repository.create(
        user.user_id,
        {
            "holder_name": user.email.split("@", 1)[0][:128],
            "masked_card_number": "•••• •••• •••• 4242",
            "expiry": "12/99",
            "status": "ACTIVE",
            "spending_limit": "100000.00",
            "currency": "INR",
            "pin_hash": None,
            "demo_mode": True,
        },
    )
    return _card(card)


@router.patch("/cards/{card_id}/status", response_model=CardResponse)
def change_card_status(
    card_id: UUID,
    payload: CardStatusRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_cards_repository),
    notifications: DemoResourceRepository = Depends(get_notifications_repository),
    demo_security: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> CardResponse:
    require_demo_mpin(demo_security, user.user_id, payload.demo_mpin)
    card = repository.get(user.user_id, str(card_id))
    if card is None:
        raise _not_found("card_not_found", "Card")
    current = card.get("status", "ACTIVE")
    next_status = {"freeze": "FROZEN", "unfreeze": "ACTIVE", "block": "BLOCKED"}[payload.action]
    if current == "BLOCKED" and payload.action == "unfreeze":
        raise AppError(code="card_blocked", message="A blocked demo card cannot be unfrozen.", status_code=409)
    updated = repository.update(user.user_id, str(card_id), {"status": next_status})
    assert updated is not None
    _create_notification(notifications, user.user_id, notification_id=f"card-status-{card_id}-{next_status}", category="CARD", title=f"Demo card {next_status.lower()}", message=f"Your fictional demo card is now {next_status.lower()}.")
    return _card(updated)


@router.patch("/cards/{card_id}/pin", response_model=CardResponse)
def change_card_pin(
    card_id: UUID,
    payload: CardPinRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_cards_repository),
    demo_security: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> CardResponse:
    require_demo_mpin(demo_security, user.user_id, payload.demo_mpin)
    if payload.pin != payload.confirm_pin:
        raise AppError(code="pin_mismatch", message="The demo PIN entries do not match.", status_code=422)
    if repository.get(user.user_id, str(card_id)) is None:
        raise _not_found("card_not_found", "Card")
    updated = repository.update(user.user_id, str(card_id), {"pin_hash": hash_password(payload.pin)})
    assert updated is not None
    return _card(updated)


@router.patch("/cards/{card_id}/limit", response_model=CardResponse)
def update_card_limit(
    card_id: UUID,
    payload: CardLimitRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_cards_repository),
    demo_security: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> CardResponse:
    require_demo_mpin(demo_security, user.user_id, payload.demo_mpin)
    if repository.get(user.user_id, str(card_id)) is None:
        raise _not_found("card_not_found", "Card")
    updated = repository.update(user.user_id, str(card_id), {"spending_limit": payload.spending_limit})
    assert updated is not None
    return _card(updated)


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(default=False),
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_notifications_repository),
) -> NotificationListResponse:
    items = repository.list(user.user_id)
    if unread_only:
        items = tuple(item for item in items if not item.get("is_read", False))
    return NotificationListResponse(notifications=[_notification(item) for item in items])


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_notifications_repository),
) -> NotificationResponse:
    document = repository.update(user.user_id, str(notification_id), {"is_read": True})
    if document is None:
        raise _not_found("notification_not_found", "Notification")
    return _notification(document)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_notifications_repository),
) -> None:
    repository.update_many(user.user_id, {"is_read": True})


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: str,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_notifications_repository),
) -> None:
    if not repository.delete(user.user_id, str(notification_id)):
        raise _not_found("notification_not_found", "Notification")


__all__ = ["router"]
