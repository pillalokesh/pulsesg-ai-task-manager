from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import TicketCategory, TicketPriority, TicketStatus


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(AuthRequest):
    fullName: str = Field(min_length=1)

    @field_validator("fullName")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fullName must not be blank")
        return value


class UserResponse(BaseModel):
    id: int
    fullName: str = Field(validation_alias="full_name")
    email: str

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class TicketRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: TicketCategory
    priority: TicketPriority

    @field_validator("title", "description")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")
    model_config = ConfigDict(from_attributes=True)


class MessageRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class MessageResponse(BaseModel):
    id: int
    message: str
    userId: int = Field(validation_alias="user_id")
    createdAt: datetime = Field(validation_alias="created_at")
    model_config = ConfigDict(from_attributes=True)


class SuggestionResponse(BaseModel):
    suggestion: str


class ProfileUpdate(BaseModel):
    fullName: str = Field(min_length=1)

    @field_validator("fullName")
    @classmethod
    def profile_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fullName must not be blank")
        return value
