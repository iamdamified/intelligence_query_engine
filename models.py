from sqlalchemy import Column, String, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from utils import uuid7, utc_now

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name = Column(String, unique=True, index=True, nullable=False)

    gender = Column(String, nullable=False, index=True)
    gender_probability = Column(Float, nullable=False, index=True)

    age = Column(Integer, nullable=False, index=True)
    age_group = Column(String, nullable=False, index=True)

    country_id = Column(String(2), nullable=False, index=True)
    country_name = Column(String, nullable=False)
    country_probability = Column(Float, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        # Common query combination
        Index("idx_profiles_gender_country", "gender", "country_id"),
        Index("idx_profiles_age_range", "age"),
        Index("idx_profiles_probabilities", "gender_probability", "country_probability"),
    )


# from sqlalchemy import Column, String, Integer, Float, DateTime
# from sqlalchemy.dialects.postgresql import UUID
# from database import Base
# from utils import uuid7, utc_now

# class Profile(Base):
#     __tablename__ = "profiles"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
#     name = Column(String, unique=True, index=True, nullable=False)

#     gender = Column(String, nullable=False)
#     gender_probability = Column(Float, nullable=False)

#     age = Column(Integer, nullable=False)
#     age_group = Column(String, nullable=False)

#     country_id = Column(String(2), nullable=False)
#     country_name = Column(String, nullable=False)
#     country_probability = Column(Float, nullable=False)
    
#     created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
