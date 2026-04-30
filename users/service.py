from sqlalchemy.orm import Session
from users.models import User
from datetime import datetime, timezone
import uuid


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


def create_test_user(db: Session, username: str, role: str = "analyst") -> User:
    """Create a test user with specified role for testing purposes."""
    # Check if user already exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    
    user = User(
        id=uuid.uuid4(),
        username=username,
        email=f"{username}@test.local",
        role=role,
        github_id=f"test-{username}",
        last_login_at=datetime.now(timezone.utc),
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    """Retrieve user by username."""
    return db.query(User).filter(User.username == username).first()