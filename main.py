from fastapi import FastAPI, Depends, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx
import re
import os
import csv
from io import StringIO

from database import Base, engine, get_db
from models import Profile
from crud import get_by_name, get_by_id, get_profiles, create, delete
from utils import uuid7, utc_now, age_group, build_pagination
from nlp_parser import parse_query

from auth.router import router as auth_router
from users.router import router as users_router
from auth.rbac import require_role
from auth.guards import secure_request

from core.responses import error
from middleware.logging import LoggingMiddleware
from middleware.rate_limiter_middleware import RateLimitMiddleware
from fastapi.responses import StreamingResponse

# --------------------
# DB INIT (DEV ONLY)
# --------------------
if os.getenv("ENV", "development") == "development":
    Base.metadata.create_all(bind=engine)

# --------------------
# APP SETUP
# --------------------
app = FastAPI(title="Insighta Labs+")
app.include_router(auth_router)
app.include_router(users_router)

# Add rate limiting middleware (before logging and CORS)
app.add_middleware(RateLimitMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------
# EXTERNAL APIS
# --------------------
GENDERIZE = "https://api.genderize.io"
AGIFY = "https://api.agify.io"
NATIONALIZE = "https://api.nationalize.io"

COUNTRY_MAP = {
    "NG": "Nigeria",
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "FR": "France",
    "GH": "Ghana",
    "KE": "Kenya",
    "ZA": "South Africa",
}

# =========================================================
# USER MANAGEMENT
# =========================================================
@app.get("/api/users/me")
def get_current_user(
    user: dict = Depends(require_role("admin", "analyst")),
    _security: dict = Depends(secure_request),
    db: Session = Depends(get_db),
):
    """Get current authenticated user info"""
    from users.service import get_user_by_id
    
    user_id = user.get("sub")
    current_user = get_user_by_id(db, user_id)
    
    if not current_user:
        return error("User not found", 404)
    
    return {
        "status": "success",
        "data": {
            "id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        }
    }


# =========================================================
# CREATE PROFILE (ADMIN ONLY)
# =========================================================
@app.post("/api/profiles", status_code=201)
async def create_profile(
    payload: dict,
    response: Response,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin")),
    _security: dict = Depends(secure_request),
):
    response.headers["Access-Control-Allow-Origin"] = "*"

    name = payload.get("name")

    if not name or not isinstance(name, str):
        return error("Invalid name", 400)

    name = name.strip().lower()

    if not re.fullmatch(r"[a-z]+", name):
        return error("Invalid name format", 400)

    existing = get_by_name(db, name)
    if existing:
        return {
            "status": "success",
            "message": "Profile already exists",
            "data": serialize_profile(existing),
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            g_res = await client.get(GENDERIZE, params={"name": name})
            a_res = await client.get(AGIFY, params={"name": name})
            n_res = await client.get(NATIONALIZE, params={"name": name})
    except httpx.RequestError:
        return error("Upstream service unavailable", 502)

    g, a, n = g_res.json(), a_res.json(), n_res.json()

    top_country = max(n["country"], key=lambda x: x["probability"])
    country_code = top_country["country_id"]

    profile = Profile(
        id=uuid7(),
        name=name,
        gender=g["gender"],
        gender_probability=g["probability"],
        age=a["age"],
        age_group=age_group(a["age"]),
        country_id=country_code,
        country_name=COUNTRY_MAP.get(country_code, country_code),
        country_probability=top_country["probability"],
        created_at=utc_now(),
    )

    create(db, profile)

    return {"status": "success", "data": serialize_profile(profile)}


# =========================================================
# LIST PROFILES
# =========================================================
@app.get("/api/profiles")
def list_profiles(
    q: str | None = None,
    gender: str | None = None,
    age_group: str | None = None,
    country_id: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin", "analyst")),
    _security: dict = Depends(secure_request),
):

    if q:
        filters = parse_query(q)
        if not filters:
            return error("Unable to interpret query", 400)
    else:
        filters = {
            k: v for k, v in {
                "gender": gender,
                "age_group": age_group,
                "country_id": country_id,
                "min_age": min_age,
                "max_age": max_age,
            }.items() if v is not None
        }

    total, data = get_profiles(
        db=db,
        filters=filters,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )

    pagination = build_pagination(
        page, limit, total,
        base_url="/api/profiles",
        query_params={"sort_by": sort_by, "order": order, **(filters or {})}
    )

    return {
        "status": "success",
        **pagination,
        "data": [serialize_profile(p) for p in data],
    }


# =========================================================
# SEARCH
# =========================================================
@app.get("/api/profiles/search")
def search_profiles(
    q: str,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin", "analyst")),
    _security: dict = Depends(secure_request),
):

    filters = parse_query(q)

    total, data = get_profiles(
        db=db,
        filters=filters,
        page=page,
        limit=limit,
    )

    pagination = build_pagination(
        page, limit, total,
        base_url="/api/profiles/search",
        query_params={"q": q}
    )

    return {
        "status": "success",
        **pagination,
        "data": [serialize_profile(p) for p in data],
    }


# =========================================================
# EXPORT CSV
# =========================================================
@app.get("/api/profiles/export")
def export_profiles(
    format: str = "csv",
    q: str | None = None,
    gender: str | None = None,
    country_id: str | None = None,
    age_group: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin", "analyst")),
    _security: dict = Depends(secure_request),
):

    if format != "csv":
        return error("Only CSV format is supported", 400)

    if q:
        filters = parse_query(q)
        if not filters:
            return error("Unable to interpret query", 400)
    else:
        filters = {
            k: v for k, v in {
                "gender": gender,
                "country_id": country_id,
                "age_group": age_group,
            }.items() if v is not None
        }

    total, data = get_profiles(
        db=db,
        filters=filters,
        page=1,
        limit=10000,
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "name", "gender", "gender_probability",
        "age", "age_group",
        "country_id", "country_name", "country_probability",
        "created_at",
    ])

    for p in data:
        writer.writerow([
            p.id,
            p.name,
            p.gender,
            p.gender_probability,
            p.age,
            p.age_group,
            p.country_id,
            p.country_name,
            p.country_probability,
            p.created_at.isoformat().replace("+00:00", "Z"),
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="profiles_export.csv"'}
    )


# =========================================================
# GET SINGLE PROFILE
# =========================================================
@app.get("/api/profiles/{profile_id}")
def get_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin", "analyst")),
    _security: dict = Depends(secure_request),
):

    profile = get_by_id(db, profile_id)

    if not profile:
        return error("Profile not found", 404)

    return {
        "status": "success",
        "data": serialize_profile(profile),
    }


# =========================================================
# DELETE PROFILE
# =========================================================
@app.delete("/api/profiles/{profile_id}")
def delete_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin")),
    _security: dict = Depends(secure_request),
):

    profile = get_by_id(db, profile_id)

    if not profile:
        return error("Profile not found", 404)

    delete(db, profile)

    return {
        "status": "success",
        "message": "Profile deleted",
    }


# --------------------
# SERIALIZER
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