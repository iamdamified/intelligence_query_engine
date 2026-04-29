import uuid, time
from datetime import datetime, timezone

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


import math

def build_pagination(page: int, limit: int, total: int, base_url: str, query_params: dict = None):
    total_pages = math.ceil(total / limit) if limit else 1

    def build_url(page_num):
        if page_num is None:
            return None
        params = query_params.copy() if query_params else {}
        params["page"] = page_num
        params["limit"] = limit
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"

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