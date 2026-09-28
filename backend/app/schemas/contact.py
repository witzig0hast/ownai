from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UtcDatetime


class _BirthdayFieldsMixin(BaseModel):
    birthday_month: int | None = Field(default=None, ge=1, le=12)
    birthday_day: int | None = Field(default=None, ge=1, le=31)
    birthday_year: int | None = Field(default=None, ge=1900, le=2100)

    @model_validator(mode="after")
    def _birthday_month_and_day_together(self) -> "_BirthdayFieldsMixin":
        if (self.birthday_month is None) != (self.birthday_day is None):
            raise ValueError("birthday_month und birthday_day müssen zusammen angegeben werden.")
        return self


class ContactCreateRequest(_BirthdayFieldsMixin):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactUpdateRequest(_BirthdayFieldsMixin):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str | None
    email: str | None
    birthday_month: int | None
    birthday_day: int | None
    birthday_year: int | None
    notes: str | None
    created_at: UtcDatetime


class ContactsListOut(BaseModel):
    contacts: list[ContactOut]
