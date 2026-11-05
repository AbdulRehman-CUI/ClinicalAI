"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Role(str, Enum):
    """Supported user roles for authorization."""

    ADMIN = "Admin"
    DOCTOR = "Doctor"
    STAFF = "Staff"


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user."""

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    role: Role = Role.STAFF

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        """Reject bcrypt truncation for new passwords, including multibyte input."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class UserLoginRequest(BaseModel):
    """Payload for authenticating a user."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class TokenRefreshRequest(BaseModel):
    """Payload for refreshing an access token."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """JWT token response envelope."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Safe user payload returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthUser(UserRead):
    """Authenticated user context for dependency injection."""
