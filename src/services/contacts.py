from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.database.models import Contact, User
from src.repository.contacts import ContactsRepository
from src.schemas import ContactModel
from sqlalchemy.exc import IntegrityError


def _handle_integrity_error(e: IntegrityError):
    if "uix_email_phone_userid" in str(e.orig):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A contact with this email or phone already exists.",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data integrity error.",
        )


class ContactsService:
    def __init__(self, db: AsyncSession):
        self.contacts_repo = ContactsRepository(db)

    async def get_contacts(
        self,
        user: User,
        skip: int = 0,
        limit: int = 100,
        name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> list[Contact]:
        return await self.contacts_repo.get_contacts(
            skip,
            limit,
            user,
            name,
            last_name,
            email,
        )

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        return await self.contacts_repo.get_contact_by_id(contact_id, user)

    async def create_contact(self, body: ContactModel, user: User) -> Contact | None:
        try:
            return await self.contacts_repo.create_contact(body, user)
        except IntegrityError as e:
            await self.contacts_repo.db.rollback()
            _handle_integrity_error(e)

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        try:
            return await self.contacts_repo.update_contact(contact_id, body, user)
        except IntegrityError as e:
            await self.contacts_repo.db.rollback()
            _handle_integrity_error(e)

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        return await self.contacts_repo.remove_contact(contact_id, user)

    async def get_upcoming_birthdays(self, user: User, days: int = 7) -> list[Contact]:
        return await self.contacts_repo.get_upcoming_birthdays(user, days)
