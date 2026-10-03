from pydantic import BaseModel, Field

from app.schemas.auth import UserOut


class AppSettingsOut(BaseModel):
    registration_open: bool
    system_paused: bool
    system_paused_message: str | None


class AppSettingsUpdateRequest(BaseModel):
    registration_open: bool | None = None
    system_paused: bool | None = None
    system_paused_message: str | None = None


class AdminUsersListOut(BaseModel):
    users: list[UserOut]


class UserApprovalRequest(BaseModel):
    approval_status: str = Field(pattern="^(approved|declined)$")
