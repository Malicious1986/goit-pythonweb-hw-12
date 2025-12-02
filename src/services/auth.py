from datetime import datetime, timedelta, UTC
from typing import Optional, Literal, Union

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt

from src.database.db import get_db
from src.conf.config import config
from src.services.users import UserService
from src.cache.user_cache import get_user_cache
from src.schemas import User as UserSchema
from src.database.models import User, UserRole


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


def create_token(
    data: dict, expires_delta: timedelta, token_type: Literal["access", "refresh"]
):
    """Create a signed JWT with standard timing claims and token type.

    The function encodes the provided payload and adds issued-at and
    expiration claims along with a ``token_type`` claim to distinguish
    between access and refresh tokens.

    Args:
        data (dict): The payload to include in the token (should include
            a ``sub`` claim for the subject).
        expires_delta (timedelta): Lifetime of the token.
        token_type (Literal["access", "refresh"]): One of ``access`` or
            ``refresh`` indicating the purpose of the token.

    Returns:
        str: The encoded JWT as a string.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + expires_delta
    to_encode.update({"exp": expire, "iat": now, "token_type": token_type})
    encoded_jwt = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return encoded_jwt


async def create_access_token(
    data: dict, expires_delta: Optional[Union[float, timedelta]] = None
):
    """Create an access JWT for short-lived authentication.

    The function accepts either a :class:`timedelta` or a numeric seconds
    value for ``expires_delta``. If none is provided, the default
    lifetime from configuration is used.

    Args:
        data (dict): Payload to include in the token (should contain ``sub``).
        expires_delta (Optional[Union[float, timedelta]]): Optional lifetime
            as a :class:`timedelta` or a number of seconds.

    Returns:
        str: Encoded access token JWT.
    """
    if isinstance(expires_delta, timedelta):
        access_token = create_token(data, expires_delta, "access")
    elif expires_delta:
        access_token = create_token(data, timedelta(seconds=expires_delta), "access")
    else:
        access_token = create_token(
            data, timedelta(seconds=config.JWT_EXPIRATION_SECONDS), "access"
        )
    return access_token


async def create_refresh_token(
    data: dict, expires_delta: Optional[Union[float, timedelta]] = None
):
    """Create a refresh JWT used to obtain new access tokens.

    Accepts the same ``expires_delta`` semantics as :func:`create_access_token`.
    Refresh tokens are typically longer-lived and are marked with a
    ``token_type`` claim of ``refresh``.

    Args:
        data (dict): Payload to include in the token (should contain ``sub``).
        expires_delta (Optional[Union[float, timedelta]]): Optional lifetime
            as a :class:`timedelta` or a number of seconds.

    Returns:
        str: Encoded refresh token JWT.
    """
    if isinstance(expires_delta, timedelta):
        refresh_token = create_token(data, expires_delta, "refresh")
    elif expires_delta:
        refresh_token = create_token(data, timedelta(seconds=expires_delta), "refresh")
    else:
        refresh_token = create_token(
            data, timedelta(seconds=config.JWT_REFRESH_EXPIRATION_SECONDS), "refresh"
        )
    return refresh_token


async def verify_refresh_token(refresh_token: str, db: AsyncSession):
    """Verify a refresh JWT and return the corresponding user.

    Decode and validate the provided refresh token, ensure the token is
    marked with a ``token_type`` of ``refresh``, then look up and return the
    database `User` whose ``username`` matches the token ``sub`` claim and
    whose stored ``refresh_token`` equals the provided token.

    Args:
        refresh_token (str): The encoded refresh JWT provided by the client.
        db (AsyncSession): Asynchronous database session for querying users.

    Returns:
        Optional[User]: The matched `User` instance when the token is valid
            and matches the stored refresh token; otherwise ``None``.

    Notes:
        JWT decoding errors are caught and the function returns ``None``
        instead of raising an exception.
    """
    try:
        payload = jwt.decode(
            refresh_token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("token_type")
        if username is None or token_type != "refresh":
            return None
        user = await db.execute(
            select(User).filter(
                User.username == username, User.refresh_token == refresh_token
            )
        )
        return user.scalars().first()
    except JWTError:
        return None


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

    cached = await get_user_cache(username)
    if cached is not None:

        return UserSchema.model_validate(cached)

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


def create_password_reset_token(data: dict, expires_seconds: int = 3600):
    """Create a short-lived JWT for password reset.

    Args:
        data (dict): Payload to include (should include a ``sub`` claim with email).
        expires_seconds (int): Token lifetime in seconds (default 1 hour).

    Returns:
        str: Encoded JWT token.
    """

    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(seconds=expires_seconds)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire, "purpose": "pwd_reset"})
    token = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token


async def get_email_from_password_reset_token(token: str):
    """Decode a password-reset token and return the email.

    Raises HTTPException on invalid/expired tokens or wrong purpose.
    """
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        if payload.get("purpose") != "pwd_reset":
            raise JWTError("Invalid token purpose")
        email = payload["sub"]
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or expired password reset token",
        )


def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user


from src.database.models import UserRole, User
