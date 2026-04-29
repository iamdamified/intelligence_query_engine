from sqlalchemy.orm import Session
from users.models import User
from datetime import datetime, timezone


def get_or_create_github_user(db: Session, github_user: dict) -> User:
    github_id = str(github_user["id"])

    user = (
        db.query(User)
        .filter(User.github_id == github_id)
        .first()
    )

    if user:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        return user

    user = User(
        github_id=github_id,
        username=github_user.get("login"),
        email=github_user.get("email"),
        avatar_url=github_user.get("avatar_url"),
        role="analyst",  # default role
        last_login_at=datetime.now(timezone.utc),
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Retrieve user by UUID."""
    return db.query(User).filter(User.id == user_id).first()