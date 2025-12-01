from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from src.database.models import Contact, User
from src.schemas import ContactModel
from datetime import date
from typing import List, cast


class ContactsRepository:
    """Repository for async CRUD operations on :class:`Contact` objects.

    The repository is scoped to a specific :class:`User` and requires an
    ``AsyncSession`` for database access. Methods enforce ownership by filtering
    on ``Contact.user_id == user.id``.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with an asynchronous DB session.

        Args:
            session (AsyncSession): Async SQLAlchemy session used for queries.
        """

        self.db = session

    async def get_contacts(
        self,
        skip: int,
        limit: int,
        user: User,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> list[Contact]:
        """Retrieve a paginated list of contacts belonging to ``user``.

        Performs optional case-insensitive partial matching on ``name``,
        ``last_name`` and ``email`` and applies pagination using ``skip`` and
        ``limit``.

        Args:
            skip (int): Number of rows to skip (offset).
            limit (int): Maximum number of rows to return.
            user (User): Owner used to scope the query.
            name (Optional[str]): Substring to match against ``Contact.name``.
            last_name (Optional[str]): Substring to match against ``Contact.last_name``.
            email (Optional[str]): Substring to match against ``Contact.email``.

        Returns:
            list[Contact]: Contacts matching filters and pagination.
        """

        stmt = select(Contact).filter_by(user_id=user.id)

        conditions = []
        if name:
            conditions.append(Contact.name.ilike(f"%{name}%"))
        if last_name:
            conditions.append(Contact.last_name.ilike(f"%{last_name}%"))
        if email:
            conditions.append(Contact.email.ilike(f"%{email}%"))
        if conditions:
            stmt = stmt.where(*conditions)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Retrieve a single contact by ``contact_id`` for ``user``.

        Args:
            contact_id (int): Primary key of the contact to fetch.
            user (User): Owner used to scope the query.

        Returns:
            Contact | None: The contact if found and owned by ``user``, otherwise ``None``.
        """

        stmt = (
            select(Contact).filter_by(user_id=user.id).where(Contact.id == contact_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        """Create a new contact and persist it to the database.

        Args:
            body (ContactModel): Input model containing contact fields.
            user (User): Owner whose id will be assigned to the new contact.

        Returns:
            Contact: The newly created and refreshed contact instance.
        """

        contact = Contact(**body.model_dump())
        contact.user_id = user.id
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        """Update fields of an existing contact owned by ``user``.

        Args:
            contact_id (int): Primary key of the contact to update.
            body (ContactModel): Input model with fields to update.
            user (User): Owner used to scope the query.

        Returns:
            Contact | None: The updated contact if it existed and was owned by
            ``user``, otherwise ``None``.
        """

        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.model_dump().items():
                setattr(contact, key, value)
            self.db.add(contact)
            await self.db.commit()
            await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Delete a contact owned by ``user``.

        Args:
            contact_id (int): Primary key of the contact to remove.
            user (User): Owner used to scope the deletion.

        Returns:
            Contact | None: The deleted contact if it existed and was owned by
            ``user``, otherwise ``None``.
        """

        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_upcoming_birthdays(self, user: User, days: int = 7) -> List[Contact]:
        """Return contacts with birthdays within the next ``days`` days.

        Only contacts with a non-null ``birth_date`` are considered. The check
        compares month/day relative to today and will roll into the next year as
        needed.

        Args:
            user (User): Owner used to scope the query.
            days (int): Window in days from today to consider (inclusive).

        Returns:
            List[Contact]: Contacts whose next birthday falls within ``days`` days.
        """

        stmt = (
            select(Contact)
            .filter_by(user_id=user.id)
            .where(Contact.birth_date.is_not(None))
        )
        result = await self.db.execute(stmt)
        contacts = list(result.scalars().all())

        today = date.today()
        upcoming: List[Contact] = []

        def next_birthday(birth: date, today: date) -> date:
            year = today.year
            candidate = date(year, birth.month, birth.day)

            if candidate < today:
                year += 1

            return candidate

        for c in contacts:
            if not c.birth_date:
                continue

            nb = next_birthday(cast(date, c.birth_date), today)
            delta = (nb - today).days
            if 0 <= delta <= days:
                upcoming.append(c)

        return upcoming
