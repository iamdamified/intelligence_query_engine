import re

COUNTRIES = {
    "nigeria": "NG",
    "kenya": "KE",
    "angola": "AO",
    "ghana": "GH",
    "south africa": "ZA"
}

def parse_query(text: str) -> dict | None:
    text = text.lower()
    filters = {}

    # gender
    if "male" in text and "female" not in text:
        filters["gender"] = "male"
    elif "female" in text and "male" not in text:
        filters["gender"] = "female"

    # age groups
    if "child" in text:
        filters["age_group"] = "child"
    elif "teenager" in text or "teen" in text:
        filters["age_group"] = "teenager"
    elif "adult" in text:
        filters["age_group"] = "adult"
    elif "senior" in text:
        filters["age_group"] = "senior"

    # young keyword (special rule)
    if "young" in text:
        filters["min_age"] = 16
        filters["max_age"] = 24

    # age comparisons
    match = re.search(r"above (\d+)", text)
    if match:
        filters["min_age"] = int(match.group(1))

    match = re.search(r"below (\d+)", text)
    if match:
        filters["max_age"] = int(match.group(1))

    # country
    for name, code in COUNTRIES.items():
        if name in text:
            filters["country_id"] = code

    return filters if filters else None