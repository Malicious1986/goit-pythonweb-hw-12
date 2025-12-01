from unittest.mock import Mock, MagicMock, AsyncMock
from fastapi import HTTPException
from src.schemas import UserCreate, RequestEmail, ResetPasswordRequest

import pytest
from sqlalchemy import select

from src.database.models import User
from tests.conftest import TestingSessionLocal
from src.services.auth import create_password_reset_token
from src.database.models import UserRole


user_data = {
    "username": "agent007",
    "email": "agent007@gmail.com",
    "password": "12345678",
    "role": "user",
}


def test_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.api.users.send_email", mock_send_email)
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "hashed_password" not in data
    assert "avatar" in data


def test_not_confirmed_login(client):
    response = client.post(
        "/api/auth/login",
        data={
            "username": user_data.get("username"),
            "password": user_data.get("password"),
        },
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Email address not verified"


@pytest.mark.asyncio
async def test_login(client):

    async with TestingSessionLocal() as session:
        current_user = await session.execute(
            select(User).where(User.email == user_data.get("email"))
        )
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()

    response = client.post(
        "/api/auth/login",
        data={
            "username": user_data.get("username"),
            "password": user_data.get("password"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data


def test_wrong_password_login(client):
    response = client.post(
        "/api/auth/login",
        data={"username": user_data.get("username"), "password": "password"},
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Invalid username or password"


def test_wrong_username_login(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "username", "password": user_data.get("password")},
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Invalid username or password"


def test_validation_error_login(client):
    response = client.post(
        "/api/auth/login", data={"password": user_data.get("password")}
    )
    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data


def test_request_email_endpoint(monkeypatch, client):
    mock_send_email = Mock()
    monkeypatch.setattr("src.api.users.send_email", mock_send_email)
    response = client.post(
        "/api/auth/request_email", json={"email": user_data["email"]}
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["message"] in (
        "Please check your email to confirm",
        "Your email is already verified",
    )


def test_password_reset_flow(client):

    token = create_password_reset_token({"sub": user_data["email"]})
    new_password = "newstrongpassword"
    response = client.post(
        "/api/auth/reset_password",
        json={"token": token, "new_password": new_password},
    )

    assert response.status_code in (200, 400), response.text


@pytest.mark.asyncio
async def test_request_email_branches(monkeypatch):
    # Case 1: user is confirmed -> returns already verified
    mock_service = MagicMock()
    user_confirmed = User(
        id=500,
        username="u500",
        email="u500@x.com",
        hashed_password="h",
        avatar=None,
        confirmed=True,
    )
    mock_service.get_user_by_email = AsyncMock(return_value=user_confirmed)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)

    background = MagicMock()
    req = MagicMock()
    req.base_url = "http://test/"
    res = await __import__("src.api.users", fromlist=["request_email"]).request_email(
        body=RequestEmail(email="u500@x.com"),
        background_tasks=background,
        request=req,
        db=MagicMock(),
    )
    assert res == {"message": "Your email is already verified"}

    # Case 2: user exists but unconfirmed -> background task added
    mock_service2 = MagicMock()
    user_unconfirmed = User(
        id=501,
        username="u501",
        email="u501@x.com",
        hashed_password="h",
        avatar=None,
        confirmed=False,
    )
    mock_service2.get_user_by_email = AsyncMock(return_value=user_unconfirmed)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service2)

    bg = MagicMock()
    bg.add_task = MagicMock()
    req2 = MagicMock()
    req2.base_url = "http://test/"
    res2 = await __import__("src.api.users", fromlist=["request_email"]).request_email(
        body=RequestEmail(email="u501@x.com"),
        background_tasks=bg,
        request=req2,
        db=MagicMock(),
    )
    # When user exists and unconfirmed, function returns prompt
    assert res2 == {"message": "Please check your email to confirm"}
    bg.add_task.assert_called_once()

    # Case 3: no user -> still returns generic prompt
    mock_service3 = MagicMock()
    mock_service3.get_user_by_email = AsyncMock(return_value=None)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service3)

    bg3 = MagicMock()
    req3 = MagicMock()
    req3.base_url = "http://test/"
    res3 = await __import__("src.api.users", fromlist=["request_email"]).request_email(
        body=RequestEmail(email="missing@x.com"),
        background_tasks=bg3,
        request=req3,
        db=MagicMock(),
    )
    assert res3 == {"message": "Please check your email to confirm"}


@pytest.mark.asyncio
async def test_request_password_reset_branches(monkeypatch):
    # Case 1: user exists -> background task added
    mock_service = MagicMock()
    user = User(
        id=600,
        username="u600",
        email="u600@x.com",
        hashed_password="h",
        avatar=None,
        confirmed=True,
    )
    mock_service.get_user_by_email = AsyncMock(return_value=user)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)

    bg = MagicMock()
    bg.add_task = MagicMock()
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "host"
    res = await __import__(
        "src.api.users", fromlist=["request_password_reset"]
    ).request_password_reset(
        body=ResetPasswordRequest(email="u600@x.com"),
        background_tasks=bg,
        request=req,
        db=MagicMock(),
    )
    assert res == {"message": "If an account with that email exists, check your inbox"}
    bg.add_task.assert_called_once()

    # Case 2: no user -> returns same generic message and no background call
    mock_service2 = MagicMock()
    mock_service2.get_user_by_email = AsyncMock(return_value=None)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service2)

    bg2 = MagicMock()
    req2 = MagicMock()
    req2.client = MagicMock()
    req2.client.host = "host"
    res2 = await __import__(
        "src.api.users", fromlist=["request_password_reset"]
    ).request_password_reset(
        body=ResetPasswordRequest(email="nope@x.com"),
        background_tasks=bg2,
        request=req2,
        db=MagicMock(),
    )
    assert res2 == {"message": "If an account with that email exists, check your inbox"}


@pytest.mark.asyncio
async def test_confirmed_email_user_not_found(monkeypatch):
    monkeypatch.setattr(
        "src.api.users.get_email_from_token",
        AsyncMock(return_value="missing@example.com"),
    )
    mock_service = MagicMock()
    mock_service.get_user_by_email = AsyncMock(return_value=None)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)

    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await __import__("src.api.users", fromlist=["confirmed_email"]).confirmed_email(
            token="t", db=db
        )

    assert exc.value.status_code == 400
    assert "Verification error" in exc.value.detail


@pytest.mark.asyncio
async def test_confirmed_email_ignores_cache_errors(monkeypatch):
    monkeypatch.setattr(
        "src.api.users.get_email_from_token", AsyncMock(return_value=user_data["email"])
    )
    mock_service = MagicMock()
    user = User(
        id=300,
        username="u300",
        email=user_data["email"],
        hashed_password="h",
        avatar=None,
        confirmed=False,
    )
    mock_service.get_user_by_email = AsyncMock(return_value=user)
    mock_service.confirmed_email = AsyncMock()
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)
    monkeypatch.setattr(
        "src.api.users.set_user_cache", AsyncMock(side_effect=Exception("cache down"))
    )

    db = MagicMock()
    res = await __import__(
        "src.api.users", fromlist=["confirmed_email"]
    ).confirmed_email(token="t", db=db)

    assert res == {"message": "Email has been verified"}


@pytest.mark.asyncio
async def test_login_invalid_password_branch(monkeypatch):
    mock_service = MagicMock()
    user = User(
        id=400,
        username="u400",
        email="u400@x.com",
        hashed_password="h",
        avatar=None,
        confirmed=True,
    )
    mock_service.get_user_by_username = AsyncMock(return_value=user)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)
    monkeypatch.setattr("src.api.users.Hash.verify_password", lambda self, a, b: False)

    form = MagicMock()
    form.username = "u400"
    form.password = "wrong"
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await __import__("src.api.users", fromlist=["login_user"]).login_user(
            form_data=form, db=db
        )

    assert exc.value.status_code == 401
    assert "Invalid username or password" in exc.value.detail


@pytest.mark.asyncio
async def test_login_raises_invalid_credentials(monkeypatch):

    mock_service = MagicMock()
    mock_service.get_user_by_username = AsyncMock(return_value=None)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)

    form = MagicMock()
    form.username = "nonexistent"
    form.password = "pw"
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await __import__("src.api.users", fromlist=["login_user"]).login_user(
            form_data=form, db=db
        )

    assert exc.value.status_code == 401
    assert "Invalid username or password" in exc.value.detail


@pytest.mark.asyncio
async def test_login_raises_unverified_email(monkeypatch):

    mock_service = MagicMock()
    user = User(
        id=200,
        username="u200",
        email="u200@x.com",
        hashed_password="h",
        avatar=None,
        confirmed=False,
    )
    mock_service.get_user_by_username = AsyncMock(return_value=user)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)
    monkeypatch.setattr("src.api.users.Hash.verify_password", lambda self, a, b: True)

    form = MagicMock()
    form.username = "u200"
    form.password = "pw"
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await __import__("src.api.users", fromlist=["login_user"]).login_user(
            form_data=form, db=db
        )

    assert exc.value.status_code == 401
    assert "Email address not verified" in exc.value.detail


@pytest.mark.asyncio
async def test_register_raises_on_existing_email(monkeypatch):
    mock_service = MagicMock()
    existing = User(
        id=99,
        username="dup",
        email=user_data["email"],
        hashed_password="h",
        avatar=None,
        confirmed=False,
        role=UserRole.USER,
    )
    mock_service.get_user_by_email = AsyncMock(return_value=existing)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)

    background = MagicMock()
    req = MagicMock()
    req.base_url = "http://test/"
    db = MagicMock()

    body = UserCreate(
        username="newuser", email=user_data["email"], password="pw", role=UserRole.USER
    )

    with pytest.raises(HTTPException) as exc:
        await __import__("src.api.users", fromlist=["register_user"]).register_user(
            user_data=body, background_tasks=background, request=req, db=db
        )

    assert exc.value.status_code == 409
    assert "A user with this email already exists" in exc.value.detail


@pytest.mark.asyncio
async def test_register_raises_on_existing_username(monkeypatch):
    mock_service = MagicMock()
    mock_service.get_user_by_email = AsyncMock(return_value=None)
    existing = User(
        id=100,
        username=user_data["username"],
        email="other@example.com",
        hashed_password="h",
        avatar=None,
        confirmed=False,
        role=UserRole.USER,
    )
    mock_service.get_user_by_username = AsyncMock(return_value=existing)
    monkeypatch.setattr("src.api.users.UserService", lambda db: mock_service)

    background = MagicMock()
    req = MagicMock()
    req.base_url = "http://test/"
    db = MagicMock()

    body = UserCreate(
        username=user_data["username"],
        email="new@example.com",
        password="pw",
        role=UserRole.USER,
    )

    with pytest.raises(HTTPException) as exc:
        await __import__("src.api.users", fromlist=["register_user"]).register_user(
            user_data=body, background_tasks=background, request=req, db=db
        )

    assert exc.value.status_code == 409
    assert "A user with this username already exists" in exc.value.detail
