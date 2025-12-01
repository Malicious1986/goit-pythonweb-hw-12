from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schemas import UserCreate


class UserRepository:
    """Repository for async CRUD operations on :class:`User` objects.

    This repository provides basic queries and persistence helpers for the
    application's ``User`` model and expects an ``AsyncSession`` for DB access.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the repository with an async DB session.

        Args:
            session (AsyncSession): Async SQLAlchemy session used for queries.
        """

        self.db = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Fetch a user by its primary key.

        Args:
            user_id (int): Primary key of the user to fetch.

        Returns:
            User | None: The user instance if found, otherwise ``None``.
        """

        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Fetch a user by username.

        Args:
            username (str): Username to search for.

        Returns:
            User | None: The user instance if found, otherwise ``None``.
        """

        stmt = select(User).filter_by(username=username)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Fetch a user by email address.

        Args:
            email (str): Email address to search for.

        Returns:
            User | None: The user instance if found, otherwise ``None``.
        """

        stmt = select(User).filter_by(email=email)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def create_user(self, body: UserCreate, avatar: str = "") -> User:
        """Create a new user record.

        Args:
            body (UserCreate): Input model with user fields.
            avatar (str): Optional avatar URL to assign.

        Returns:
            User: The newly created and refreshed user instance.
        """

        user = User(
            **body.model_dump(exclude_unset=True, exclude={"password"}),
            hashed_password=body.password,
            avatar=avatar,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> None:
        """Mark a user's email as confirmed.

        If a user with the provided email exists, set ``confirmed=True`` and
        commit the change.

        Args:
            email (str): Email address of the user to confirm.

        Returns:
            None
        """

        user: User | None = await self.get_user_by_email(email)
        if user is not None:
            user.confirmed = True
            await self.db.commit()
        return None

    async def update_avatar_url(self, email: str, url: str) -> User | None:
        """Update the avatar URL for a user identified by email.

        Args:
            email (str): Email of the user to update.
            url (str): New avatar URL.

        Returns:
            User | None: Updated user instance if found, otherwise ``None``.
        """

        user = await self.get_user_by_email(email)
        if user is None:
            return None
        user.avatar = url
        await self.db.commit()
        await self.db.refresh(user)
        return user
