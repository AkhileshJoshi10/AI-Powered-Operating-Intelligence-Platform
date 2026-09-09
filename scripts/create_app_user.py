from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

load_dotenv(
    PROJECT_ROOT / ".env",
    override=False,
)

from backend.app.services.auth_service import (  # noqa: E402
    create_app_user,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create one local application user without exposing "
            "passwords on the command line."
        ),
    )

    parser.add_argument(
        "--email",
        required=True,
    )
    parser.add_argument(
        "--name",
        required=True,
    )
    parser.add_argument(
        "--role",
        required=True,
        choices=[
            "Admin",
            "Manager",
            "Viewer",
        ],
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    password = getpass(
        "Password: "
    )
    password_confirmation = getpass(
        "Confirm password: "
    )

    if password != password_confirmation:
        raise SystemExit(
            "Passwords do not match."
        )

    result = create_app_user(
        email=args.email,
        full_name=args.name,
        password=password,
        role=args.role,
    )

    user = result.get(
        "user"
    )

    if result["outcome"] == "duplicate":
        raise SystemExit(
            "An application user with that email already exists."
        )

    print(
        "Created application user:",
        user["email"],
        f"({user['role']})",
    )


if __name__ == "__main__":
    main()
