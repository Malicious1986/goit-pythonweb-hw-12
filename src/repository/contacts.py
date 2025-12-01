from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from src.database.models import Contact, User
from src.schemas import ContactModel
from datetime import date
from typing import List, cast


class ContactsRepository:
    def __init__(self, session: AsyncSession):
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
        stmt = (
            select(Contact).filter_by(user_id=user.id).where(Contact.id == contact_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        contact = Contact(**body.model_dump())
        contact.user_id = user.id
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.model_dump().items():
                setattr(contact, key, value)
            self.db.add(contact)
            await self.db.commit()
            await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def get_upcoming_birthdays(self, user: User, days: int = 7) -> List[Contact]:
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
