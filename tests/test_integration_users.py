import pytest
from unittest.mock import Mock

from src.services.auth import create_email_token
from src.services.auth import Hash
from src.database.models import User
from tests.conftest import test_user
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_me_endpoint(client, get_token):
    token = get_token

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "username" in data


def test_confirmed_email_already_verified(client):

    token = create_email_token({"sub": test_user["email"]})
    response = client.get(f"/api/auth/confirmed_email/{token}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "Your email is already verified"


@pytest.mark.asyncio
async def test_request_email_for_unconfirmed_user(client, monkeypatch):

    async with TestingSessionLocal() as session:
        pwd = "pw123456"
        hash_password = Hash().get_password_hash(pwd)
        tmp_user = User(
            username="tmpuser",
            email="tmpuser@example.com",
            hashed_password=hash_password,
            confirmed=False,
            avatar="",
        )
        session.add(tmp_user)
        await session.commit()

    mock_send = Mock()
    monkeypatch.setattr("src.api.users.send_email", mock_send)

    response = client.post(
        "/api/auth/request_email", json={"email": "tmpuser@example.com"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "Please check your email to confirm"


@pytest.mark.asyncio
async def test_update_avatar_endpoint(client, get_token, monkeypatch):
    token = get_token

    monkeypatch.setattr(
        "src.api.users.UploadFileService.upload_file",
        staticmethod(lambda file, username: "http://avatar.example/img.png"),
    )

    files = {"file": ("avatar.png", b"data", "image/png")}
    response = client.patch(
        "/api/auth/avatar", headers={"Authorization": f"Bearer {token}"}, files=files
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("avatar") == "http://avatar.example/img.png"
