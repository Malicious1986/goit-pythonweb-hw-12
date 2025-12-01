import pytest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.users import UserRepository
from src.schemas import UserCreate


@pytest.fixture
def mock_session():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest.fixture
def user_repository(mock_session):
    return UserRepository(mock_session)


@pytest.fixture
def user():
    return User(
        id=1,
        username="testuser",
        email="user@example.com",
        hashed_password="pw",
        avatar="",
        confirmed=False,
    )


@pytest.mark.asyncio
async def test_get_user_by_id(user_repository, mock_session, user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    res = await user_repository.get_user_by_id(user_id=1)

    assert res is user


@pytest.mark.asyncio
async def test_get_user_by_username(user_repository, mock_session, user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    res = await user_repository.get_user_by_username(username="testuser")

    assert res is user


@pytest.mark.asyncio
async def test_get_user_by_email(user_repository, mock_session, user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    res = await user_repository.get_user_by_email(email="user@example.com")

    assert res is user


@pytest.mark.asyncio
async def test_create_user(user_repository, mock_session):
    body = UserCreate(username="newuser", email="new@example.com", password="secret")

    res = await user_repository.create_user(body=body, avatar="http://avatar")

    assert isinstance(res, User)
    assert res.username == "newuser"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(res)


@pytest.mark.asyncio
async def test_confirmed_email_sets_flag(user_repository, mock_session, user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    await user_repository.confirmed_email(email=user.email)

    assert user.confirmed is True
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmed_email_no_user_does_nothing(user_repository, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    await user_repository.confirmed_email(email="noone@example.com")

    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_avatar_url(user_repository, mock_session, user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    res = await user_repository.update_avatar_url(email=user.email, url="http://new")

    assert res is user
    assert res.avatar == "http://new"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_update_avatar_url_not_found(user_repository, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    res = await user_repository.update_avatar_url(
        email="noone@example.com", url="http://no"
    )

    assert res is None
