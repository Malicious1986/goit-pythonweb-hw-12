from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database.db import get_db
from src.conf.config import config
from src.services.users import UserService


class Hash:
    """Password hashing utilities using :class:`passlib.context.CryptContext`.

    Methods are thin wrappers around the configured ``pwd_context``.
    """

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        """Verify a plain password against a stored hash.

        Args:
            plain_password (str): The plaintext password to verify.
            hashed_password (str): The stored password hash.

        Returns:
            bool: True if the password matches, False otherwise.
        """

        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """Hash the provided password using the configured algorithms.

        Args:
            password (str): Plaintext password.

        Returns:
            str: Hashed password.
        """

        return self.pwd_context.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def create_access_token(data: dict, expires_delta: Optional[int] = None):
    """Create a JWT access token for the provided payload.

    Args:
        data (dict): Payload to encode (should include a ``sub`` claim).
        expires_delta (Optional[int]): Expiration in seconds. When omitted the default from configuration is used.

    Returns:
        str: Encoded JWT.
    """

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(UTC) + timedelta(seconds=config.JWT_EXPIRATION_SECONDS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    """Resolve the currently authenticated user from a bearer token.

    This dependency decodes the JWT, extracts the ``sub`` claim as the
    username and loads the corresponding user from the database.

    Raises a 401 HTTPException if decoding fails or the user is not found.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        username = payload["sub"]
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception
    user_service = UserService(db)
    user = await user_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


def create_email_token(data: dict):
    """Create a short-lived token used for email verification.

    Args:
        data (dict): Payload to include (should include a ``sub`` claim with email).

    Returns:
        str: Encoded JWT token.
    """

    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token


async def get_email_from_token(token: str):
    """Decode an email verification token and return the email.

    Args:
        token (str): Encoded JWT token.

    Returns:
        str: Email address stored in the token's ``sub`` claim.

    Raises:
        HTTPException: 422 if token decoding fails or the token is invalid.
    """

    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        email = payload["sub"]
        return email
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid token for email verification",
        )
