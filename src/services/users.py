from sqlalchemy.ext.asyncio import AsyncSession

from libgravatar import Gravatar

from src.repository.users import UserRepository
from src.schemas import UserCreate


class UserService:
    """High-level user operations that orchestrate repository actions.

    The service wraps :class:`UserRepository` to provide application-level
    behavior such as avatar generation and simple error handling.
    """

    def __init__(self, db: AsyncSession):
        """Create a new service instance with a DB session.

        Args:
            db (AsyncSession): Async database session.
        """

        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        """Create a user and optionally generate an avatar URL.

        Args:
            body (UserCreate): Input model containing new user data.

        Returns:
            User: The newly created user instance.
        """

        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(e)

        return await self.repository.create_user(body, avatar or "")

    async def get_user_by_id(self, user_id: int):
        """Return a user by id.

        Args:
            user_id (int): ID of the user to retrieve.

        Returns:
            User | None: The user if found, otherwise ``None``.
        """

        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str):
        """Return a user by username.

        Args:
            username (str): Username to look up.

        Returns:
            User | None: The user if found, otherwise ``None``.
        """

        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str):
        """Return a user by email.

        Args:
            email (str): Email to look up.

        Returns:
            User | None: The user if found, otherwise ``None``.
        """

        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        """Mark the given user's email as confirmed.

        Args:
            email (str): Email of the user to confirm.

        Returns:
            None
        """

        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        """Update the avatar URL for a user.

        Args:
            email (str): Email of the user to update.
            url (str): New avatar URL.

        Returns:
            User | None: Updated user if found, otherwise ``None``.
        """

        return await self.repository.update_avatar_url(email, url)
