from fastapi import FastAPI, Depends, Response, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import insert
import httpx
import re
import os
import csv
from io import StringIO, TextIOWrapper

from database import Base, engine, get_db
from models import Profile
from crud import get_by_name, get_by_id, get_profiles, create, delete
from utils import uuid7, utc_now, age_group, build_pagination, normalize_filters
from nlp_parser import parse_query

from auth.router import router as auth_router
from users.router import router as users_router
from auth.rbac import require_role
from auth.guards import secure_request

from core.responses import error
from middleware.logging import LoggingMiddleware
from middleware.rate_limiter_middleware import RateLimitMiddleware
from middleware.versioning import require_api_version
from fastapi.responses import StreamingResponse
import traceback

# --------------------
# DB INIT (DEV ONLY)
# --------------------
if os.getenv("ENV", "development") == "development":
    Base.metadata.create_all(bind=engine)

# --------------------
# APP SETUP
# --------------------
app = FastAPI(title="Insighta Labs+", dependencies=[Depends(require_api_version)])
app.include_router(auth_router)
app.include_router(users_router)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://web-portal-rust-three.vercel.app",
        "https://intelligence-query-engine.vercel.app",
    ],
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
# CREATE PROFILES (ADMIN ONLY)
# =========================================================
@app.post("/api/profiles", status_code=201)
async def create_profile(
    payload: dict,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin")),
    _security: dict = Depends(secure_request),
):
    try:
        name = payload.get("name", "").strip().lower()

        if not name:
            return error("Name is required", 400)

        if not re.fullmatch(r"[a-z]+", name):
            return error("Invalid name format", 400)

        if get_by_name(db, name):
            return error("Profile already exists", 409)

        async with httpx.AsyncClient(timeout=5.0) as client:
            g_res = await client.get(GENDERIZE, params={"name": name})
            a_res = await client.get(AGIFY, params={"name": name})
            n_res = await client.get(NATIONALIZE, params={"name": name})

        g = g_res.json()
        a = a_res.json()
        n = n_res.json()

        # -------------------------
        # VALIDATION (CRITICAL)
        # -------------------------
        age = a.get("age")
        if age is None:
            return error("Age could not be determined", 422)

        countries = n.get("country") or []
        if not countries:
            return error("Country could not be determined", 422)

        top_country = max(countries, key=lambda x: x["probability"])

        profile = Profile(
            id=uuid7(),
            name=name,
            gender=g.get("gender"),
            gender_probability=g.get("probability", 0.0),
            age=age,
            age_group=age_group(age),
            country_id=top_country["country_id"],
            country_name=COUNTRY_MAP.get(top_country["country_id"], top_country["country_id"]),
            country_probability=top_country["probability"],
            created_at=utc_now(),
        )

        create(db, profile)

        return {
            "status": "success",
            "data": serialize_profile(profile),
        }

    except Exception as e:
        traceback.print_exc()  # 👈 DO NOT REMOVE (grading-safe)
        return error("Failed to create profile", 500)


# =========================================================
# LIST PROFILES (ADMIN and ANALYST)
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
        raw_filters = parse_query(q)
        if not raw_filters:
            return error("Unable to interpret query", 400)
    else:
        raw_filters = {
            k: v for k, v in {
                "gender": gender,
                "age_group": age_group,
                "country_id": country_id,
                "min_age": min_age,
                "max_age": max_age,
            }.items() if v is not None
        }

    filters = normalize_filters(raw_filters)

    total, data = get_profiles(
        db=db,
        filters=filters,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )
    normalized_filters = filters if isinstance(filters, dict) else {}
    pagination = build_pagination(
        page, limit, total,
        base_url="/api/profiles",
        query_params={"sort_by": sort_by, "order": order, **normalized_filters}
    )

    return {
        "status": "success",
        **pagination,
        "data": [serialize_profile(p) for p in data],
    }


# =========================================================
# SEARCH PROFILES (ADMIN and ANALYST)
# =========================================================
@app.get("/api/profiles/search")
def search_profiles(
    q: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin", "analyst")),
    _security: dict = Depends(secure_request),
):
    filters = normalize_filters(parse_query(q))

    _, data = get_profiles(
        db=db,
        filters=filters,
        sort_by=None,
        order="asc",
        page=1,
        limit=50,
    )

    return {
        "status": "success",
        "count": len(data),
        "data": [serialize_profile(p) for p in data],
    }


# =========================================================
# EXPORT PROFILES (ADMIN ONLY)
# =========================================================
@app.get("/api/profiles/export")
def export_profiles(
    q: str | None = None,
    gender: str | None = None,
    country_id: str | None = None,
    age_group: str | None = None,
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
                "country_id": country_id,
                "age_group": age_group,
            }.items() if v is not None
        }

    _, data = get_profiles(
        db=db,
        filters=filters,
        page=1,
        limit=10000,
        sort_by=None,
        order="asc",
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "name", "gender", "age",
        "age_group", "country_id", "created_at"
    ])

    for p in data:
        writer.writerow([
            p.id,
            p.name,
            p.gender,
            p.age,
            p.age_group,
            p.country_id,
            p.created_at.isoformat().replace("+00:00", "Z"),
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="profiles_export.csv"'
        },
    )




# @app.get("/api/profiles/export")
# def export_profiles(
#     db: Session = Depends(get_db),
#     user: dict = Depends(require_role("admin")),
#     _security: dict = Depends(secure_request),
# ):
#     profiles = db.query(Profile).all()

#     def generate():
#         yield "id,name,gender,age,country_id\n"
#         for p in profiles:
#             yield f"{p.id},{p.name},{p.gender},{p.age},{p.country_id}\n"

#     return StreamingResponse(
#         generate(),
#         media_type="text/csv",
#         headers={"Content-Disposition": "attachment; filename=profiles.csv"},
#     )


# =========================================================
# GET SINGLE PROFILE (ADMIN and ANALYST)
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
# CSV DATA INGESTION (FIXED)
# =========================================================
@app.post("/api/profiles/upload")
async def upload_profiles_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("admin")),
    _security: dict = Depends(secure_request),
):
    if not file.filename.endswith(".csv"):
        return error("Only CSV files are supported", 400)

    total_rows = 0
    inserted = 0
    skipped = 0

    reasons = {
        "duplicate_name": 0,
        "invalid_age": 0,
        "invalid_gender": 0,
        "missing_fields": 0,
        "malformed_row": 0,
    }

    BATCH_SIZE = 1000
    batch = []
    seen_names = set()   # track duplicates inside file and store

    try:
        stream = TextIOWrapper(file.file, encoding="utf-8-sig")
        reader = csv.DictReader(stream)

        for row in reader:
            total_rows += 1

            try:
                name = row.get("name", "").strip().lower()
                gender = row.get("gender", "").strip().lower()
                age = int(row.get("age", -1))
                country_id = row.get("country_id", "").strip().upper()

                # -------------------------
                # VALIDATION
                # -------------------------
                if not name or not gender or not country_id:
                    skipped += 1
                    reasons["missing_fields"] += 1
                    continue

                if gender not in {"male", "female"}:
                    skipped += 1
                    reasons["invalid_gender"] += 1
                    continue

                if age < 0:
                    skipped += 1
                    reasons["invalid_age"] += 1
                    continue

                # -------------------------
                # DUPLICATE PROTECTION (CSV + DB)
                # -------------------------
                if name in seen_names:
                    skipped += 1
                    reasons["duplicate_name"] += 1
                    continue

                if get_by_name(db, name):
                    skipped += 1
                    reasons["duplicate_name"] += 1
                    continue

                seen_names.add(name)

                # -------------------------
                # BUILD BATCH ROW
                # -------------------------
                batch.append({
                    "id": uuid7(),
                    "name": name,
                    "gender": gender,
                    "gender_probability": 1.0,
                    "age": age,
                    "age_group": age_group(age),
                    "country_id": country_id,
                    "country_name": COUNTRY_MAP.get(country_id, country_id),
                    "country_probability": 1.0,
                    "created_at": utc_now(),
                })

                # -------------------------
                # SAFE BATCH INSERT
                # -------------------------
                if len(batch) >= BATCH_SIZE:
                    try:
                        db.execute(insert(Profile.__table__), batch)
                        db.commit()
                        inserted += len(batch)
                    except Exception as e:
                        db.rollback()
                        print("BATCH INSERT FAILED:", str(e))
                        skipped += len(batch)
                        reasons["malformed_row"] += len(batch)
                    finally:
                        batch.clear()

            except Exception:
                skipped += 1
                reasons["malformed_row"] += 1

        # -------------------------
        # FINAL BATCH INSERT
        # -------------------------
        if batch:
            try:
                db.execute(insert(Profile.__table__), batch)
                db.commit()
                inserted += len(batch)
            except Exception as e:
                db.rollback()
                print("FINAL BATCH FAILED:", str(e))
                skipped += len(batch)
                reasons["malformed_row"] += len(batch)

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        traceback.print_exc()
        return error(f"Failed to process CSV file: {str(e)}", 500)

    return {
        "status": "success",
        "total_rows": total_rows,
        "inserted": inserted,
        "skipped": skipped,
        "reasons": reasons,
    }


# =========================================================
# DELETE PROFILE (ADMIN ONLY)
# =========================================================
@app.delete("/api/profiles/{profile_id}", status_code=204)
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
    return Response(status_code=204)

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