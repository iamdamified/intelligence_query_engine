from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    username: str | None
    email: EmailStr | None
    avatar_url: str | None
    role: str
    is_active: bool


class UserRead(UserBase):
    id: UUID
    github_id: str | None
    last_login_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True