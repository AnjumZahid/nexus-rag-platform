import argparse
from datetime import timedelta

from backend.app.auth import get_jwt_service


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local development JWT token."
        )
    )

    parser.add_argument(
        "--user-id",
        required=True,
    )

    parser.add_argument(
        "--organization-id",
        required=True,
    )

    parser.add_argument(
        "--expires-minutes",
        type=int,
        default=60,
    )

    arguments = parser.parse_args()

    if arguments.expires_minutes < 1:
        raise ValueError(
            "expires-minutes must be at least 1."
        )

    token = get_jwt_service().create_access_token(
        user_id=arguments.user_id,
        organization_id=(
            arguments.organization_id
        ),
        expires_delta=timedelta(
            minutes=arguments.expires_minutes
        ),
    )

    print("\nDevelopment access token:\n")
    print(token)
    print(
        "\nDo not commit or publicly share this token."
    )


if __name__ == "__main__":
    main()


# uv run python -m scripts.create_dev_token `
#     --user-id test-user `
#     --organization-id test-org `
#     --expires-minutes 60


# =========
# The token will print in the terminal.