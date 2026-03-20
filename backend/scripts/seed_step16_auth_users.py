from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.db.enums import UserRole, UserStatus
from app.db.models import User
from app.modules.auth.security import hash_password

DEFAULT_PASSWORD = "voltiq123"
DEFAULT_USERS: tuple[tuple[str, UserRole], ...] = (
    ("operator_demo", UserRole.OPERATOR),
    ("sales_demo", UserRole.SALES),
    ("manager_demo", UserRole.MANAGER),
)


def _upsert_demo_user(db: Session, username: str, role: UserRole) -> tuple[User, bool]:
    user = db.query(User).filter(User.username == username).first()
    now = dt.datetime.now(dt.timezone.utc)
    if user is None:
        user = User(
            id=uuid.uuid4(),
            username=username,
            password_hash=hash_password(DEFAULT_PASSWORD),
            role=role,
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        return user, True

    user.role = role
    user.status = UserStatus.ACTIVE
    user.password_hash = hash_password(DEFAULT_PASSWORD)
    user.updated_at = now
    return user, False


def main() -> None:
    with SessionLocal() as db:
        created = 0
        updated = 0
        for username, role in DEFAULT_USERS:
            _, is_created = _upsert_demo_user(db, username, role)
            if is_created:
                created += 1
            else:
                updated += 1
        db.commit()

    print("Step 16 demo users are ready.")
    print(f"Created: {created}, Updated: {updated}")
    print(f"Default password: {DEFAULT_PASSWORD}")
    print("Users: operator_demo / sales_demo / manager_demo")


if __name__ == "__main__":
    main()

