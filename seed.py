import json
from database import SessionLocal
from models import Profile
from utils import uuid7, utc_now, age_group


def seed():
    db = SessionLocal()

    with open("seed_profiles.json", "r") as f:
        data = json.load(f)
        profiles = data["profiles"]

    total = len(profiles)
    inserted = 0
    skipped = 0

    print(f"\n🚀 Starting seed process...")
    print(f"📦 Total profiles to process: {total}\n")

    try:
        for i, p in enumerate(profiles, start=1):

            name = p["name"].strip().lower()

            # 📊 progress tracker
            percent = (i / total) * 100
            print(f"[{i}/{total} - {percent:.2f}%] Processing: {name}")

            exists = db.query(Profile).filter(Profile.name.ilike(name)).first()

            if exists:
                skipped += 1
                print(f"   ↳ ⏭ skipped (already exists)\n")
                continue

            profile = Profile(
                id=uuid7(),
                name=name,
                gender=p.get("gender"),
                gender_probability=p.get("gender_probability", 0),
                age=p.get("age"),
                age_group=p.get("age_group") or age_group(p.get("age")),
                country_id=p.get("country_id"),
                country_name=p.get("country_name", p.get("country_id")),
                country_probability=p.get("country_probability", 0),
                created_at=p.get("created_at", utc_now()),
            )

            db.add(profile)
            inserted += 1

            print(f"   ↳ ✅ inserted\n")

        db.commit()

    except Exception as e:
        db.rollback()
        print("Seeding failed:", e)

    finally:
        db.close()

    print("\n SEED SUMMARY")
    print("----------------")
    print("Inserted:", inserted)
    print("Skipped:", skipped)
    print("Total processed:", total)


if __name__ == "__main__":
    seed()