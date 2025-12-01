import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.repository.contacts import ContactsRepository
from src.schemas import ContactModel


@pytest.fixture
def mock_session():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def contact_repository(mock_session):
    return ContactsRepository(mock_session)


@pytest.fixture
def user():
    return User(id=1, username="testuser")


@pytest.mark.asyncio
async def test_get_contacts(contact_repository, mock_session, user):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        Contact(
            id=1,
            name="John",
            last_name="Doe",
            email="j@example.com",
            phone="123",
            user=user,
        )
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    contacts = await contact_repository.get_contacts(skip=0, limit=10, user=user)

    assert len(contacts) == 1
    assert contacts[0].name == "John"


@pytest.mark.asyncio
async def test_get_contact_by_id(contact_repository, mock_session, user):
    existing = Contact(
        id=1,
        name="Jane",
        last_name="Smith",
        email="s@example.com",
        phone="321",
        user=user,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    contact = await contact_repository.get_contact_by_id(contact_id=1, user=user)

    assert contact is not None
    assert contact.id == 1
    assert contact.name == "Jane"


@pytest.mark.asyncio
async def test_create_contact(contact_repository, mock_session, user):
    contact_data = ContactModel(
        name="New",
        last_name="Person",
        email="new@example.com",
        phone="555",
        additional_info="",
    )

    result = await contact_repository.create_contact(body=contact_data, user=user)

    assert isinstance(result, Contact)
    assert result.name == "New"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_update_contact(contact_repository, mock_session, user):
    existing = Contact(
        id=1,
        name="Old",
        last_name="Person",
        email="o@example.com",
        phone="000",
        user=user,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    body = ContactModel(
        name="Updated",
        last_name="Person",
        email="u@example.com",
        phone="000",
        additional_info="",
    )

    updated = await contact_repository.update_contact(
        contact_id=1, body=body, user=user
    )

    assert updated is not None
    assert updated.name == "Updated"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing)


@pytest.mark.asyncio
async def test_remove_contact(contact_repository, mock_session, user):
    existing = Contact(
        id=1,
        name="ToDelete",
        last_name="Person",
        email="d@example.com",
        phone="999",
        user=user,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await contact_repository.remove_contact(contact_id=1, user=user)

    assert result is not None
    assert result.name == "ToDelete"
    mock_session.delete.assert_awaited_once_with(existing)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_upcoming_birthdays(contact_repository, mock_session, user):
    today = date.today()
    days = 7

    contact_in = Contact(
        id=1,
        name="In",
        last_name="Birthday",
        email="in@example.com",
        phone="111",
        birth_date=date(1990, today.month, today.day),
        user=user,
    )

    future_target = today + timedelta(days=days + 5)
    contact_out = Contact(
        id=2,
        name="Out",
        last_name="Birthday",
        email="out@example.com",
        phone="222",
        birth_date=date(1990, future_target.month, future_target.day),
        user=user,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [contact_in, contact_out]
    mock_session.execute = AsyncMock(return_value=mock_result)

    upcoming = await contact_repository.get_upcoming_birthdays(user=user, days=days)

    assert len(upcoming) == 1
    assert upcoming[0].name == "In"
