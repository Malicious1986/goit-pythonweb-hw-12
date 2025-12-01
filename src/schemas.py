from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class ContactModel(BaseModel):
    name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: EmailStr = Field(max_length=50)
    phone: str = Field(max_length=20)
    birth_date: Optional[date] = None
    additional_info: Optional[str] = Field(None, max_length=250)

    @field_validator("birth_date")
    def validate_birthdate(cls, v: Optional[date]):
        if v is None:
            return None
        today = date.today()
        if v > today:
            raise ValueError("birth_date cannot be in the future")
        if v < date(1900, 1, 1):
            raise ValueError("birth_date is too far in the past")
        return v


class ContactResponseModel(ContactModel):
    id: int

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    id: int
    username: str
    email: str
    avatar: str
    confirmed: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str
