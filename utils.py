import uuid, time, math
from datetime import datetime, timezone
from typing import Dict, Any, Tuple


def uuid7():
    ts = int(time.time() * 1000)
    rand = uuid.uuid4().int >> 80
    return str(uuid.UUID(int=(ts << 80) | rand))


def utc_now():
    return datetime.now(timezone.utc)


def age_group(age: int) -> str:
    if age <= 12:
        return "child"
    if age <= 19:
        return "teenager"
    if age <= 59:
        return "adult"
    return "senior"


# -------------------------------------------------
# Pagination (FIX 2: total may be None)
# -------------------------------------------------
def build_pagination(
    page: int,
    limit: int,
    total: int | None,
    base_url: str,
    query_params: dict | None = None,
):
    def build_url(page_num):
        if page_num is None:
            return None
        params = query_params.copy() if query_params else {}
        params["page"] = page_num
        params["limit"] = limit
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    # When total is skipped (page > 1)
    if total is None:
        return {
            "page": page,
            "limit": limit,
            "total": None,
            "total_pages": None,
            "links": {
                "self": build_url(page),
                "next": build_url(page + 1),
                "prev": build_url(page - 1 if page > 1 else None),
            },
        }

    total_pages = math.ceil(total / limit) if limit else 1

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {
            "self": build_url(page),
            "next": build_url(page + 1 if page < total_pages else None),
            "prev": build_url(page - 1 if page > 1 else None),
        },
    }


# -------------------------------------------------
# Query normalization (FIX 1)
# -------------------------------------------------
def normalize_filters(
    filters: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], Tuple[Tuple[str, Any], ...]]:
    """
    Returns:
    - normalized_dict → used for DB execution & pagination
    - canonical_tuple → used ONLY for cache keys
    """
    if not filters:
        return {}, ()

    normalized = {}

    for key, value in filters.items():
        if isinstance(value, str):
            if key == "country_id":
                normalized[key] = value.upper()
            else:
                normalized[key] = value.lower()
        else:
            normalized[key] = value

    canonical = tuple(sorted(normalized.items()))
    return normalized, canonical


