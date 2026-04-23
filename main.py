from fastapi import FastAPI, Depends, Response, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx
import re
import os

from database import Base, engine, SessionLocal
from models import Profile
from crud import (
    get_by_name,
    get_by_id,
    get_all,
    get_profiles,
    create,
    delete,
)
from utils import uuid7, utc_now, age_group
from nlp_parser import parse_query

# --------------------
# DATABASE INIT (DEV ONLY)
# --------------------
if os.getenv("ENV", "development") == "development":
    Base.metadata.create_all(bind=engine)

# --------------------
# APP SETUP
# --------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # REQUIRED BY GRADER
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------
# EXTERNAL APIS (STAGE 1)
# --------------------
GENDERIZE = "https://api.genderize.io"
AGIFY = "https://api.agify.io"
NATIONALIZE = "https://api.nationalize.io"

# --------------------
# DB DEPENDENCY
# --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


COUNTRY_MAP = {
    "NG": "Nigeria",
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "FR": "France",
    "GH": "Ghana",
    "KE": "Kenya",
    "ZA": "South Africa",
    # add more as needed
}

# --------------------
# CREATE PROFILE (STAGE 1 – UNCHANGED LOGIC)
# --------------------
@app.post("/api/profiles", status_code=201)
async def create_profile(payload: dict, response: Response, db: Session = Depends(get_db)):
    response.headers["Access-Control-Allow-Origin"] = "*"

    name = payload.get("name")

    # -------- VALIDATION --------
    if name is None or (isinstance(name, str) and not name.strip()):
        return JSONResponse({"status": "error", "message": "Missing or empty name"}, 400)

    if not isinstance(name, str):
        return JSONResponse({"status": "error", "message": "Invalid type"}, 422)

    name = name.strip().lower()

    if not re.fullmatch(r"[a-z]+", name):
        return JSONResponse(
            {"status": "error", "message": "Name must contain alphabetic characters only"},
            400,
        )

    # -------- IDEMPOTENCY --------
    existing = get_by_name(db, name)
    if existing:
        return {
            "status": "success",
            "message": "Profile already exists",
            "data": serialize_profile(existing),
        }

    # -------- EXTERNAL API CALLS --------
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            g_res = await client.get(GENDERIZE, params={"name": name})
            a_res = await client.get(AGIFY, params={"name": name})
            n_res = await client.get(NATIONALIZE, params={"name": name})
    except httpx.RequestError:
        return JSONResponse(
            {"status": "error", "message": "Upstream service unavailable"}, 502
        )

    try:
        g, a, n = g_res.json(), a_res.json(), n_res.json()
    except ValueError:
        return JSONResponse(
            {"status": "error", "message": "Upstream service returned invalid JSON"}, 502
        )

    # -------- UPSTREAM VALIDATION --------
    if g.get("gender") is None or g.get("count", 0) == 0:
        return JSONResponse(
            {"status": "error", "message": "Genderize returned an invalid response"}, 502
        )

    if a.get("age") is None:
        return JSONResponse(
            {"status": "error", "message": "Agify returned an invalid response"}, 502
        )

    if not n.get("country"):
        return JSONResponse(
            {"status": "error", "message": "Nationalize returned an invalid response"}, 502
        )

    top_country = max(n["country"], key=lambda x: x["probability"])
    country_code = top_country["country_id"]

    # -------- CREATE PROFILE --------
    profile = Profile(
        id=uuid7(),
        name=name,
        gender=g["gender"],
        gender_probability=g["probability"],
        age=a["age"],
        age_group=age_group(a["age"]),
        # country_id=top_country["country_id"],
        # country_name=top_country.get("country_id"),
        country_id=country_code,
        country_name=COUNTRY_MAP.get(country_code, country_code),
        country_probability=top_country["probability"],
        created_at=utc_now(),
    )

    create(db, profile)

    return {"status": "success", "data": serialize_profile(profile)}

# --------------------
# GET ALL PROFILES
# (REST FILTERS OR NLP QUERY)
# --------------------
@app.get("/api/profiles")
def list_profiles(
    q: str | None = None,
    gender: str | None = None,
    age_group: str | None = None,
    country_id: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    min_gender_probability: float | None = None,
    min_country_probability: float | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    # ---------- NLP MODE ----------
    if q:
        filters = parse_query(q)
        if not filters:
            return JSONResponse(
                {"status": "error", "message": "Unable to interpret query"}, 400
            )

    # ---------- STRUCTURED FILTER MODE ----------
    else:
        filters = {
            k: v
            for k, v in {
                "gender": gender,
                "age_group": age_group,
                "country_id": country_id,
                "min_age": min_age,
                "max_age": max_age,
                "min_gender_probability": min_gender_probability,
                "min_country_probability": min_country_probability,
            }.items()
            if v is not None
        }

    total, data = get_profiles(
        db=db,
        filters=filters or None,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )

    if data is None:
        return JSONResponse(
            {"status": "error", "message": "Invalid query parameters"}, 400
        )

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize_profile(p) for p in data],
    }
# def list_profiles(
#     q: str | None = None,
#     gender: str | None = None,
#     age_group: str | None = None,
#     country_id: str | None = None,
#     sort_by: str | None = None,
#     order: str = "asc",
#     page: int = Query(1, ge=1),
#     limit: int = Query(10, ge=1, le=50),
#     db: Session = Depends(get_db),
# ):
#     # -------- OPTION 1: ENFORCE MODE SEPARATION --------
#     if q and (gender or age_group or country_id):
#         return JSONResponse(
#             {
#                 "status": "error",
#                 "message": "Do not combine 'q' with structured filters (gender, age_group, country_id)"
#             },
#             400,
#         )

#     # -------- STAGE 2: NLP QUERY MODE --------
#     if q:
#         filters = parse_query(q)
#         if not filters:
#             return JSONResponse(
#                 {"status": "error", "message": "Unable to interpret query"}, 400
#             )

#         total, data = get_profiles(
#             db=db,
#             filters=filters,
#             sort_by=sort_by,
#             order=order,
#             page=page,
#             limit=limit,
#         )

#         if data is None:
#             return JSONResponse(
#                 {"status": "error", "message": "Invalid query parameters"}, 400
#             )

#         return {
#             "status": "success",
#             "page": page,
#             "limit": limit,
#             "total": total,
#             "data": [serialize_profile(p) for p in data],
#         }

#     # -------- STAGE 1: BASIC FILTER MODE --------
#     profiles = get_all(
#         db=db,
#         gender=gender,
#         country_id=country_id,
#         age_group=age_group,
#     )

#     return {
#         "status": "success",
#         "count": len(profiles),
#         "data": [serialize_profile(p) for p in profiles],
#     }


@app.get("/api/profiles/search")
def search_profiles(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    sort_by: str | None = None,
    order: str = "asc",
    db: Session = Depends(get_db),
):
    filters = parse_query(q)
    if not filters:
        return JSONResponse(
            {"status": "error", "message": "Unable to interpret query"}, 400
        )

    total, data = get_profiles(
        db=db,
        filters=filters,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize_profile(p) for p in data],
    }
# --------------------
# GET SINGLE PROFILE
# --------------------
@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = get_by_id(db, profile_id)
    if not profile:
        return JSONResponse(
            {"status": "error", "message": "Profile not found"}, 404
        )
    return {"status": "success", "data": serialize_profile(profile)}

# --------------------
# DELETE PROFILE
# --------------------
@app.delete("/api/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = get_by_id(db, profile_id)
    if not profile:
        return JSONResponse(
            {"status": "error", "message": "Profile not found"}, 404
        )
    delete(db, profile)
    return JSONResponse(
        {"status": "success", "message": "Profile deleted"}, 200
    )

# --------------------
# SERIALIZER (UTC ISO 8601)
# --------------------
def serialize_profile(p: Profile):
    return {
        "id": p.id,
        "name": p.name,
        "gender": p.gender,
        "gender_probability": p.gender_probability,
        "age": p.age,
        "age_group": p.age_group,
        "country_id": p.country_id,
        "country_name": p.country_name,
        "country_probability": p.country_probability,
        "created_at": p.created_at.isoformat().replace("+00:00", "Z"),
    }

