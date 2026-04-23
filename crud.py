from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Profile

SORT_FIELDS = {
    "age": Profile.age,
    "created_at": Profile.created_at,
    "gender_probability": Profile.gender_probability,
}


# ---------- Read helpers ----------

def get_by_name(db: Session, name: str):
    return db.query(Profile).filter(Profile.name == name).first()


def get_by_id(db: Session, id):
    return db.query(Profile).filter(Profile.id == id).first()


def get_all(
    db: Session,
    gender: str | None = None,
    country_id: str | None = None,
    age_group: str | None = None,
):
    query = db.query(Profile)

    if gender:
        query = query.filter(Profile.gender == gender.lower())

    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())

    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())

    return query.all()


# ---------- Stage 2 NLP + pagination query ----------

def get_profiles(
    db: Session,
    filters: dict | None,
    sort_by: str | None,
    order: str,
    page: int,
    limit: int,
):
    query = db.query(Profile)

    if filters:
        if "gender" in filters:
            query = query.filter(Profile.gender == filters["gender"])

        if "age_group" in filters:
            query = query.filter(Profile.age_group == filters["age_group"])

        if "country_id" in filters:
            query = query.filter(Profile.country_id == filters["country_id"])

        if "min_age" in filters:
            query = query.filter(Profile.age >= filters["min_age"])

        if "max_age" in filters:
            query = query.filter(Profile.age <= filters["max_age"])

        # REQUIRED BY SPEC
        if "min_gender_probability" in filters:
            query = query.filter(
                Profile.gender_probability >= filters["min_gender_probability"]
            )

        # REQUIRED BY SPEC
        if "min_country_probability" in filters:
            query = query.filter(
                Profile.country_probability >= filters["min_country_probability"]
            )

    total = query.count()

    if sort_by:
        column = SORT_FIELDS.get(sort_by)
        if not column:
            return None, None
        query = query.order_by(
            column.desc() if order == "desc" else column.asc()
        )

    offset = (page - 1) * limit
    data = query.offset(offset).limit(limit).all()

    return total, data

# def get_profiles(
#     db: Session,
#     filters: dict | None,
#     sort_by: str | None,
#     order: str,
#     page: int,
#     limit: int,
# ):
#     query = db.query(Profile)

#     if filters:
#         if "gender" in filters:
#             query = query.filter(Profile.gender == filters["gender"])

#         if "age_group" in filters:
#             query = query.filter(Profile.age_group == filters["age_group"])

#         if "country_id" in filters:
#             query = query.filter(Profile.country_id == filters["country_id"])

#         if "min_age" in filters:
#             query = query.filter(Profile.age >= filters["min_age"])

#         if "max_age" in filters:
#             query = query.filter(Profile.age <= filters["max_age"])

#     total = query.count()

#     if sort_by:
#         column = SORT_FIELDS.get(sort_by)
#         if not column:
#             return None, None
#         query = query.order_by(
#             column.desc() if order == "desc" else column.asc()
#         )

#     offset = (page - 1) * limit
#     data = query.offset(offset).limit(limit).all()

#     return total, data


# ---------- Write helpers ----------

def create(db: Session, profile: Profile):
    try:
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError:
        db.rollback()
        raise


def delete(db: Session, profile: Profile):
    try:
        db.delete(profile)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise



# from sqlalchemy.orm import Session
# from models import Profile

# SORT_FIELDS = {
#     "age": Profile.age,
#     "created_at": Profile.created_at,
#     "gender_probability": Profile.gender_probability,
# }

# def get_profiles(db: Session, filters: dict, sort_by: str, order: str, page: int, limit: int):
#     query = db.query(Profile)

#     if filters:
#         if "gender" in filters:
#             query = query.filter(Profile.gender == filters["gender"])

#         if "age_group" in filters:
#             query = query.filter(Profile.age_group == filters["age_group"])

#         if "country_id" in filters:
#             query = query.filter(Profile.country_id == filters["country_id"])

#         if "min_age" in filters:
#             query = query.filter(Profile.age >= filters["min_age"])

#         if "max_age" in filters:
#             query = query.filter(Profile.age <= filters["max_age"])

#     total = query.count()

#     if sort_by:
#         column = SORT_FIELDS.get(sort_by)
#         if not column:
#             return None, None
#         query = query.order_by(column.desc() if order == "desc" else column.asc())

#     offset = (page - 1) * limit
#     data = query.offset(offset).limit(limit).all()

#     return total, data



# from sqlalchemy.orm import Session
# from models import Profile
# from sqlalchemy.exc import SQLAlchemyError

# def get_by_name(db: Session, name: str):
#     return db.query(Profile).filter(Profile.name == name).first()

# def get_by_id(db: Session, id: str):
#     return db.query(Profile).filter(Profile.id == id).first()

# def get_all(db: Session, gender=None, country_id=None, age_group=None):
#     q = db.query(Profile)
#     if gender:
#         q = q.filter(Profile.gender == gender.lower())
#     if country_id:
#         q = q.filter(Profile.country_id == country_id.upper())
#     if age_group:
#         q = q.filter(Profile.age_group == age_group.lower())
#     return q.all()

# def create(db: Session, profile: Profile):
#     try:
#         db.add(profile)
#         db.commit()
#         db.refresh(profile)
#         return profile
#     except SQLAlchemyError:
#         db.rollback()
#         raise

# def delete(db: Session, profile: Profile):
#     try:
#         db.delete(profile)
#         db.commit()
#     except SQLAlchemyError:
#         db.rollback()
#         raise