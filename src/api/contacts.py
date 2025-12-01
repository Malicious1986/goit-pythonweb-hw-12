"""Contacts API endpoints.

This module exposes REST endpoints for managing contact records. Each
operation is protected by authentication and delegates business logic to
``src.services.contacts.ContactsService``.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User
from src.services.auth import get_current_user
from src.database.db import get_db
from src.schemas import ContactResponseModel, ContactModel
from src.services.contacts import ContactsService


router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=List[ContactResponseModel])
async def get_contacts(
    skip: int = 0,
    limit: int = 100,
    name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of contacts for the current user.

    Args:
        skip (int): Offset for pagination.
        limit (int): Maximum number of results.
        name (str | None): Optional name filter.
        last_name (str | None): Optional last name filter.
        email (str | None): Optional email filter.
        user (User): Authenticated user (injected).
        db (AsyncSession): Database session (injected).

    Returns:
        list[ContactResponseModel]: List of contact response models.
    """

    contacts_service = ContactsService(db)
    contacts = await contacts_service.get_contacts(
        user, skip, limit, name, last_name, email
    )
    return contacts


@router.get("/upcoming", response_model=List[ContactResponseModel])
async def get_upcoming_birthdays(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return contacts whose birthdays occur within the next `days` days.

    Args:
        days (int): Window of days to consider (inclusive).
        db (AsyncSession): Database session (injected).
        user (User): Authenticated user (injected).

    Returns:
        list[ContactResponseModel]: Contacts with upcoming birthdays.
    """

    contacts_service = ContactsService(db)
    return await contacts_service.get_upcoming_birthdays(user, days)


@router.get("/{contact_id}", response_model=ContactResponseModel | None)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return a single contact by id for the authenticated user.

    Args:
        contact_id (int): Contact primary key.
        db (AsyncSession): Database session (injected).
        user (User): Authenticated user (injected).

    Returns:
        ContactResponseModel | None: Contact if found and owned by user.
    """

    contacts_service = ContactsService(db)
    return await contacts_service.get_contact_by_id(contact_id, user)


@router.post("/", response_model=ContactResponseModel)
async def create_contact(
    body: ContactModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new contact for the authenticated user.

    Args:
        body (ContactModel): Input payload for the contact.
        db (AsyncSession): Database session (injected).
        user (User): Authenticated user (injected).

    Returns:
        ContactResponseModel: Created contact.
    """

    contacts_service = ContactsService(db)
    return await contacts_service.create_contact(body, user)


@router.put("/{contact_id}", response_model=ContactResponseModel | None)
async def update_contact(
    contact_id: int,
    body: ContactModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an existing contact owned by the authenticated user.

    Args:
        contact_id (int): Contact primary key to update.
        body (ContactModel): Fields to update.
        db (AsyncSession): Database session (injected).
        user (User): Authenticated user (injected).

    Returns:
        ContactResponseModel | None: Updated contact or ``None`` if not found.
    """

    contacts_service = ContactsService(db)
    return await contacts_service.update_contact(contact_id, body, user)


@router.delete("/{contact_id}", response_model=ContactResponseModel | None)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a contact owned by the authenticated user.

    Args:
        contact_id (int): Contact primary key to delete.
        db (AsyncSession): Database session (injected).
        user (User): Authenticated user (injected).

    Returns:
        ContactResponseModel | None: Deleted contact or ``None`` if not found.
    """

    contacts_service = ContactsService(db)
    return await contacts_service.remove_contact(contact_id, user)
