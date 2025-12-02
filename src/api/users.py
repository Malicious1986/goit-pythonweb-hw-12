from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    BackgroundTasks,
    Request,
    UploadFile,
    File,
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from src.schemas import RequestEmail, UserCreate, Token, User, TokenRefreshRequest
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    Hash,
    get_current_user,
    get_current_admin_user,
)
from src.cache.user_cache import set_user_cache, delete_user_cache
from src.schemas import User
from src.services.mail import send_email
from src.services.mail import send_password_reset_email
from src.services.auth import get_email_from_password_reset_token
from src.schemas import ResetPasswordRequest, ResetPasswordConfirm
from src.services.upload_file import UploadFileService
from src.services.users import UserService
from src.database.db import get_db
from src.services.auth import get_email_from_token
from src.conf.limiter import limiter
from src.conf.config import config

"""Authentication and user-related API endpoints.

Endpoints include registration, login, retrieval of the authenticated user,
email confirmation flows, and avatar upload.
"""

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and send an email verification task.

    Performs uniqueness checks on username and email, hashes the password,
    creates the user, and enqueues an email verification task in the
    background tasks.

    Args:
        user_data (UserCreate): Incoming user creation payload.
        background_tasks (BackgroundTasks): FastAPI background task runner.
        request (Request): FastAPI request object (used to determine host).
        db (AsyncSession): Database session (injected).

    Returns:
        User: The newly created user.
    """

    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(user_data.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    username_user = await user_service.get_user_by_username(user_data.username)
    if username_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists",
        )
    user_data.password = Hash().get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data)
    client = getattr(request, "client", None)
    host = client.host if client is not None else str(request.base_url)
    background_tasks.add_task(send_email, new_user.email, new_user.username, host)
    return new_user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Authenticate a user and return an access token.

    Validates credentials and confirmed email status before issuing a JWT.

    Args:
        form_data (OAuth2PasswordRequestForm): Form data containing username/password.
        db (AsyncSession): Database session (injected).

    Returns:
        dict: Token response with ``access_token`` and ``token_type``.
    """

    user_service = UserService(db)
    user = await user_service.get_user_by_username(form_data.username)
    if not user or not Hash().verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address not verified",
        )

    access_token = await create_access_token(data={"sub": user.username})
    refresh_token = await create_refresh_token(data={"sub": user.username})
    user.refresh_token = refresh_token

    try:
        await set_user_cache(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "avatar": user.avatar or "",
                "confirmed": bool(user.confirmed),
                "role": user.role,
                "refresh_token": user.refresh_token,
            }
        )
    except Exception:

        pass
    await db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh-token", response_model=Token)
async def new_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token.

    Verifies the provided refresh token and returns a new access token
    while echoing the original refresh token back to the client.

    Args:
        request (TokenRefreshRequest): Payload containing the refresh token.
        db (AsyncSession, optional): Database session dependency provided
            by FastAPI's dependency injection.

    Returns:
        dict: A mapping with keys ``access_token``, ``refresh_token``, and
            ``token_type``.

    Raises:
        HTTPException: If the refresh token is invalid or expired
            (HTTP 401 Unauthorized).
    """
    user = await verify_refresh_token(request.refresh_token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    new_access_token = await create_access_token(data={"sub": user.username})
    return {
        "access_token": new_access_token,
        "refresh_token": request.refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=User)
@limiter.limit("5/minute")
@limiter.limit("1/second")
async def me(request: Request, user: User = Depends(get_current_user)):
    """Return the currently authenticated user.

    Rate-limited endpoint that returns the authenticated user's data.
    """

    return user


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify an email confirmation token and mark user's email as confirmed.

    Args:
        token (str): Email verification token.
        db (AsyncSession): Database session (injected).

    Returns:
        dict: Message indicating verification status.
    """

    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already verified"}
    await user_service.confirmed_email(email)

    try:
        await set_user_cache(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "avatar": user.avatar or "",
                "confirmed": True,
                "role": user.role,
            }
        )
    except Exception:
        pass
    return {"message": "Email has been verified"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request a new verification email for the provided address.

    If the user exists and is unconfirmed, a verification email is enqueued.

    Args:
        body (RequestEmail): Payload containing the email address.
        background_tasks (BackgroundTasks): Background task runner.
        request (Request): FastAPI request (used to build base URL).
        db (AsyncSession): Database session (injected).

    Returns:
        dict: Message instructing the caller to check their email.
    """

    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user and user.confirmed:
        return {"message": "Your email is already verified"}
    if user:
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
    return {"message": "Please check your email to confirm"}


@router.post("/request_password_reset")
async def request_password_reset(
    body: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request a password-reset email.

    For security, this endpoint always returns a generic message so it does
    not reveal whether the email is registered.
    """

    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user:
        client = getattr(request, "client", None)
        host = client.host if client is not None else str(request.base_url)
        background_tasks.add_task(
            send_password_reset_email, user.email, user.username, host
        )
    return {"message": "If an account with that email exists, check your inbox"}


@router.post("/reset_password")
async def reset_password(
    body: ResetPasswordConfirm, db: AsyncSession = Depends(get_db)
):
    """Reset a user's password using a valid reset token.

    The token encodes the target email; if valid, the user's password is updated.
    """

    email = await get_email_from_password_reset_token(body.token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token or user"
        )

    hashed = Hash().get_password_hash(body.new_password)
    updated_user = await user_service.update_password(email, hashed)

    try:
        await delete_user_cache(user.username)
    except Exception:
        pass

    return {"message": "Password has been reset successfully"}


@router.patch("/avatar", response_model=User)
async def update_avatar_user(
    file: UploadFile = File(),
    user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and set a new avatar image for the authenticated user.

    Args:
        file (UploadFile): Uploaded file object.
        user (User): Authenticated user (injected).
        db (AsyncSession): Database session (injected).

    Returns:
        User: Updated user model with new avatar URL.
    """

    avatar_url = UploadFileService(
        config.CLOUDINARY_NAME, config.CLOUDINARY_API_KEY, config.CLOUDINARY_API_SECRET
    ).upload_file(file, user.username)

    user_service = UserService(db)
    updated_user = await user_service.update_avatar_url(user.email, avatar_url)

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        await set_user_cache(
            {
                "id": updated_user.id,
                "username": updated_user.username,
                "email": updated_user.email,
                "avatar": updated_user.avatar or "",
                "confirmed": bool(updated_user.confirmed),
                "role": updated_user.role,
            }
        )
    except Exception:
        pass

    return User.model_validate(updated_user)
