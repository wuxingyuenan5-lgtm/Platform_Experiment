from __future__ import annotations

import argparse
from getpass import getpass

from app.database import initialize_database
from app.schema_migrations import apply_platform_migrations
from app.user_repository import InitialCeoAlreadyExistsError
from app.user_service import create_initial_ceo


def create_ceo_interactively() -> int:
    username = input("Username: ").strip()
    display_name = input("Display name: ").strip() or None
    real_name = input("Real name: ").strip() or None
    email = input("Email (optional): ").strip() or None
    phone = input("Phone (optional): ").strip() or None
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        print("Password confirmation does not match")
        return 2
    initialize_database()
    apply_platform_migrations()
    try:
        created = create_initial_ceo(
            username=username,
            password=password,
            display_name=display_name,
            real_name=real_name,
            email=email,
            phone=phone,
        )
    except InitialCeoAlreadyExistsError:
        print("An active CEO already exists")
        return 3
    print(f"Created initial CEO account: {created.username}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="User-system administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create-ceo", help="Create the first CEO interactively")
    arguments = parser.parse_args()
    if arguments.command == "create-ceo":
        return create_ceo_interactively()
    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
