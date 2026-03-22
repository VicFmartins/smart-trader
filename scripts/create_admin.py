from __future__ import annotations

import argparse
import getpass

from app.db.session import session_scope
from app.services.auth import AuthService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update the first admin user for Smart Trade.")
    parser.add_argument("--email", required=True, help="Admin email used to sign in.")
    parser.add_argument("--full-name", default="Platform Admin", help="Optional display name for the user.")
    parser.add_argument("--password", help="Admin password. If omitted, you will be prompted securely.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = args.password or getpass.getpass("Admin password: ")
    if not password.strip():
        raise SystemExit("Password must not be empty.")

    with session_scope() as db:
        user, created = AuthService(db).create_or_update_user(
            email=args.email,
            password=password,
            full_name=args.full_name,
            is_admin=True,
            is_active=True,
        )

    action = "created" if created else "updated"
    print(f"Admin user {action}: {user.email} (id={user.id})")


if __name__ == "__main__":
    main()
