"""Create the first Super Admin after ``alembic upgrade head``."""

from __future__ import annotations

import argparse

from sqlalchemy import select

from palms_api.config import get_settings
from palms_api.database import Database
from palms_api.models import Role, User
from palms_api.schemas import PasswordValue
from palms_api.security import hash_password
from palms_api.seeding import seed_system_rbac


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    email = args.email.strip().lower()
    if "@" not in email:
        raise SystemExit("--email must be a valid email address.")
    try:
        password = PasswordValue(password=args.password).password
    except ValueError as error:
        raise SystemExit(f"--password is invalid: {error}") from error

    database = Database(get_settings())
    session = database.session_factory()
    try:
        seed_system_rbac(session)
        existing = session.scalar(select(User.id).where(User.email == email))
        if existing is not None:
            raise SystemExit("A user with that email already exists.")
        role = session.scalar(select(Role).where(Role.name == "Super Admin"))
        if role is None:
            raise SystemExit("Super Admin role is missing; run alembic upgrade head first.")
        session.add(
            User(
                email=email,
                full_name=args.name.strip(),
                password_hash=hash_password(password),
                role_id=role.id,
            )
        )
        session.commit()
    finally:
        session.close()
        database.dispose()


if __name__ == "__main__":
    main()
