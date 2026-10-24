from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import UtcDatetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=255)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    is_admin: bool
    approval_status: str
    created_at: UtcDatetime
    sso_linked: bool
    home_city: str | None
    briefing_enabled: bool
    briefing_hour: int
    briefing_minute: int


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    # Empty string clears it.
    home_city: str | None = Field(default=None, max_length=255)
    briefing_enabled: bool | None = None
    briefing_hour: int | None = Field(default=None, ge=0, le=23)
    briefing_minute: int | None = Field(default=None, ge=0, le=59)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
