from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class ProfileOut(BaseModel):
    id: UUID
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: datetime

    class Config:
        orm_mode = True