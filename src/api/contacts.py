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
    contacts_service = ContactsService(db)
    return await contacts_service.get_upcoming_birthdays(user, days)


@router.get("/{contact_id}", response_model=ContactResponseModel | None)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contacts_service = ContactsService(db)
    return await contacts_service.get_contact_by_id(contact_id, user)


@router.post("/", response_model=ContactResponseModel)
async def create_contact(
    body: ContactModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contacts_service = ContactsService(db)
    return await contacts_service.create_contact(body, user)


@router.put("/{contact_id}", response_model=ContactResponseModel | None)
async def update_contact(
    contact_id: int,
    body: ContactModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contacts_service = ContactsService(db)
    return await contacts_service.update_contact(contact_id, body, user)


@router.delete("/{contact_id}", response_model=ContactResponseModel | None)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contacts_service = ContactsService(db)
    return await contacts_service.remove_contact(contact_id, user)
