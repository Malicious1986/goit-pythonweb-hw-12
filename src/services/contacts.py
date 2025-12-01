from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.database.models import Contact, User
from src.repository.contacts import ContactsRepository
from src.schemas import ContactModel
from sqlalchemy.exc import IntegrityError


def _handle_integrity_error(e: IntegrityError):
    """Map SQLAlchemy IntegrityError to a FastAPI HTTPException.

    Args:
        e (IntegrityError): The raised SQLAlchemy IntegrityError.

    Raises:
        HTTPException: 409 if unique constraint for email/phone is violated,
            otherwise 400 for general integrity errors.
    """

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
    """Service layer for contact-related business logic.

    The service wraps :class:`ContactsRepository` and translates DB-level
    integrity errors into HTTP exceptions.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the contacts service with a DB session.

        Args:
            db (AsyncSession): Async database session.
        """

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
        """Return a paginated list of user's contacts.

        Args:
            user (User): Owner to scope the query.
            skip (int): Offset for pagination.
            limit (int): Maximum number of results.
            name (str | None): Optional name filter.
            last_name (str | None): Optional last name filter.
            email (str | None): Optional email filter.

        Returns:
            list[Contact]: Contacts matching filters.
        """

        return await self.contacts_repo.get_contacts(
            skip,
            limit,
            user,
            name,
            last_name,
            email,
        )

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Fetch a contact by id scoped to ``user``.

        Args:
            contact_id (int): Contact primary key.
            user (User): Owner used to scope the query.

        Returns:
            Contact | None: The contact if found, otherwise ``None``.
        """

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
        """Remove a contact owned by ``user``.

        Args:
            contact_id (int): Contact primary key to remove.
            user (User): Owner used to scope the deletion.

        Returns:
            Contact | None: The deleted contact if it existed, otherwise ``None``.
        """

        return await self.contacts_repo.remove_contact(contact_id, user)

    async def get_upcoming_birthdays(self, user: User, days: int = 7) -> list[Contact]:
        """Return contacts with upcoming birthdays for ``user`` within ``days``.

        Args:
            user (User): Owner used to scope the query.
            days (int): Days window to check (inclusive).

        Returns:
            list[Contact]: Contacts with upcoming birthdays.
        """

        return await self.contacts_repo.get_upcoming_birthdays(user, days)
