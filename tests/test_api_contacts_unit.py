import pytest
from unittest.mock import AsyncMock, MagicMock

from src.api import contacts as contacts_api
from src.schemas import ContactModel
from src.database.models import User


@pytest.mark.asyncio
async def test_get_contacts_delegates(monkeypatch):
    mock_service = MagicMock()
    mock_service.get_contacts = AsyncMock(return_value=[{"id": 1}])
    monkeypatch.setattr("src.api.contacts.ContactsService", lambda db: mock_service)

    user = User(id=1, username="u")
    db = MagicMock()

    res = await contacts_api.get_contacts(
        skip=0, limit=10, name="a", last_name="b", email="c", user=user, db=db
    )

    assert res == [{"id": 1}]
    mock_service.get_contacts.assert_awaited_once_with(user, 0, 10, "a", "b", "c")


@pytest.mark.asyncio
async def test_get_upcoming_birthdays_delegates(monkeypatch):
    mock_service = MagicMock()
    mock_service.get_upcoming_birthdays = AsyncMock(return_value=[{"id": 2}])
    monkeypatch.setattr("src.api.contacts.ContactsService", lambda db: mock_service)

    user = User(id=2, username="u2")
    db = MagicMock()

    res = await contacts_api.get_upcoming_birthdays(days=5, db=db, user=user)

    assert res == [{"id": 2}]
    mock_service.get_upcoming_birthdays.assert_awaited_once_with(user, 5)


@pytest.mark.asyncio
async def test_get_contact_delegates(monkeypatch):
    mock_service = MagicMock()
    mock_service.get_contact_by_id = AsyncMock(return_value={"id": 3})
    monkeypatch.setattr("src.api.contacts.ContactsService", lambda db: mock_service)

    user = User(id=3, username="u3")
    db = MagicMock()

    res = await contacts_api.get_contact(contact_id=3, db=db, user=user)

    assert res == {"id": 3}
    mock_service.get_contact_by_id.assert_awaited_once_with(3, user)


@pytest.mark.asyncio
async def test_create_contact_delegates(monkeypatch):
    mock_service = MagicMock()
    mock_service.create_contact = AsyncMock(return_value={"id": 4})
    monkeypatch.setattr("src.api.contacts.ContactsService", lambda db: mock_service)

    user = User(id=4, username="u4")
    db = MagicMock()
    body = ContactModel(
        name="N",
        last_name="L",
        email="e@example.com",
        phone="123",
        additional_info="info",
    )

    res = await contacts_api.create_contact(body=body, db=db, user=user)

    assert res == {"id": 4}
    mock_service.create_contact.assert_awaited_once_with(body, user)


@pytest.mark.asyncio
async def test_update_contact_delegates(monkeypatch):
    mock_service = MagicMock()
    mock_service.update_contact = AsyncMock(return_value={"id": 5})
    monkeypatch.setattr("src.api.contacts.ContactsService", lambda db: mock_service)

    user = User(id=5, username="u5")
    db = MagicMock()
    body = ContactModel(
        name="N",
        last_name="L",
        email="e2@example.com",
        phone="321",
        additional_info="info",
    )

    res = await contacts_api.update_contact(contact_id=5, body=body, db=db, user=user)

    assert res == {"id": 5}
    mock_service.update_contact.assert_awaited_once_with(5, body, user)


@pytest.mark.asyncio
async def test_delete_contact_delegates(monkeypatch):
    mock_service = MagicMock()
    mock_service.remove_contact = AsyncMock(return_value={"id": 6})
    monkeypatch.setattr("src.api.contacts.ContactsService", lambda db: mock_service)

    user = User(id=6, username="u6")
    db = MagicMock()

    res = await contacts_api.delete_contact(contact_id=6, db=db, user=user)

    assert res == {"id": 6}
    mock_service.remove_contact.assert_awaited_once_with(6, user)
