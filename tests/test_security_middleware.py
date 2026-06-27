from fastapi.testclient import TestClient

from backend.app.api.app import create_app


def main() -> None:
    app = create_app()

    valid_request_id = (
        "security-test-request-123"
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={
                "Origin": (
                    "http://localhost:3000"
                ),
                "X-Request-ID": (
                    valid_request_id
                ),
            },
        )

        assert response.status_code == 200

        assert (
            response.headers["x-request-id"]
            == valid_request_id
        )

        assert (
            response.headers[
                "x-content-type-options"
            ]
            == "nosniff"
        )

        assert (
            response.headers[
                "x-frame-options"
            ]
            == "DENY"
        )

        assert (
            response.headers[
                "referrer-policy"
            ]
            == "no-referrer"
        )

        assert (
            "x-process-time-ms"
            in response.headers
        )

        assert (
            response.headers[
                "access-control-allow-origin"
            ]
            == "http://localhost:3000"
        )

        invalid_id_response = client.get(
            "/api/v1/health",
            headers={
                "X-Request-ID": "bad request id!",
            },
        )

        assert (
            invalid_id_response.status_code
            == 200
        )

        generated_request_id = (
            invalid_id_response.headers[
                "x-request-id"
            ]
        )

        assert generated_request_id
        assert (
            generated_request_id
            != "bad request id!"
        )

        untrusted_host_response = client.get(
            "/api/v1/health",
            headers={
                "Host": "malicious.example",
            },
        )

        assert (
            untrusted_host_response.status_code
            == 400
        )

        print(
            "\n=== SECURITY MIDDLEWARE TEST ==="
        )
        print(
            "Trusted request ID confirmed."
        )
        print(
            "Invalid request ID replacement "
            "confirmed."
        )
        print(
            "Security headers confirmed."
        )
        print(
            "Process-time header confirmed."
        )
        print(
            "CORS origin confirmed."
        )
        print(
            "Untrusted host rejection confirmed."
        )
        print(
            "Security middleware test "
            "passed successfully."
        )


if __name__ == "__main__":
    main()

# uv run python -m tests.test_security_middleware