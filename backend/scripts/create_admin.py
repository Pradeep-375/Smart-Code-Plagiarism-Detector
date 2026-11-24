"""Create an administrator, or promote an existing account to administrator, from the command line.

This is the supported way to add admins without going through public registration:

    cd backend
    python scripts/create_admin.py --email you@example.com --name "Your Name"      # prompts for the password

The password is read with getpass (or from the ADMIN_PASSWORD environment variable for automation); it is never
accepted as a command-line argument, so it does not end up in shell history. Works against whatever DATABASE_URL points at.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app import models  # noqa: E402,F401
from app.core.security import hash_password, validate_password_strength  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.seed import seed_base  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", default="System Administrator")
    ap.add_argument("--promote", action="store_true", help="if the e-mail already exists, make that account an admin and keep its password")
    args = ap.parse_args()
    email = args.email.strip().lower()

    if str(engine.url).startswith("sqlite"):
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_base(db)  # makes sure roles exist
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            if not args.promote:
                print(f"{email} already exists (role: {existing.role_name}). Re-run with --promote to make it an admin.", file=sys.stderr)
                return 1
            existing.role_id, existing.is_active = admin_role.id, True
            db.commit()
            print(f"Promoted {email} to admin.")
            return 0
        password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
        if not os.environ.get("ADMIN_PASSWORD") and password != getpass.getpass("Repeat password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
        try:
            validate_password_strength(password)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        db.add(User(email=email, full_name=args.name.strip(), hashed_password=hash_password(password), role_id=admin_role.id))
        db.commit()
        print(f"Created admin {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
