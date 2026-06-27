
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from backend.app.api.app import create_app
from backend.app.api.dependencies import (
    get_db_session,
    get_shared_embedding_provider,
    get_shared_llm_provider,
)
from backend.app.auth import get_jwt_service


class FakeVectorStore:
    """In-memory vector-store replacement for API tests."""

    def similarity_search(
        self,
        query: str,
        *,
        k: int | None = None,
        document_id: str | None = None,
    ) -> list[Document]:
        return [
            Document(
                page_content=(
                    "A healthy diet and regular physical "
                    "activity are recommended."
                ),
                metadata={
                    "citation_id": "S1",
                    "document_id": (
                        document_id or "document-123"
                    ),
                    "chunk_id": "chunk-1",
                    "filename": "guidelines.pdf",
                    "page_number": 10,
                    "organization_id": "test-org",
                    "user_id": "test-user",
                    "knowledge_base_id": "test-kb",
                },
            )
        ]

    def close(self) -> None:
        """Close the fake vector store."""

        return None


class FakeLLMProvider:
    """Deterministic LLM replacement for tests."""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return (
            "A healthy diet and physical activity "
            "are recommended [S1]."
        )


class FakeIngestionService:
    """Document-ingestion replacement for tests."""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        pass

    async def ingest_pdf(
        self,
        *,
        file_path,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
    ):
        return SimpleNamespace(
            document_id="document-123",
            status="completed",
            total_pages=2,
            chunk_count=3,
            vector_ids=(
                "v1",
                "v2",
                "v3",
            ),
        )


class FakeDatabaseResult:
    """
    SQLAlchemy-result replacement.

    It returns an active owner membership for valid
    authenticated test requests.
    """

    def scalar_one_or_none(self):
        return SimpleNamespace(
            id="membership-123",
            organization_id="test-org",
            user_id="test-user",
            role="owner",
            is_active=True,
        )


class FakeDatabaseSession:
    """
    Async database-session replacement.

    The organization-access dependency calls
    session.execute(), so the fake session must implement
    that method.
    """

    async def execute(
        self,
        *args,
        **kwargs,
    ) -> FakeDatabaseResult:
        return FakeDatabaseResult()


async def fake_db_session():
    """Provide a fake async database session."""

    yield FakeDatabaseSession()


def main() -> None:
    app = create_app()

    app.dependency_overrides[
        get_db_session
    ] = fake_db_session

    app.dependency_overrides[
        get_shared_embedding_provider
    ] = lambda: object()

    app.dependency_overrides[
        get_shared_llm_provider
    ] = lambda: FakeLLMProvider()

    fake_vector_store = FakeVectorStore()

    try:
        with (
            patch(
                "backend.app.api.routes."
                "get_vector_store",
                return_value=fake_vector_store,
            ),
            patch(
                "backend.app.api.routes."
                "DocumentIngestionService",
                FakeIngestionService,
            ),
            TestClient(app) as client,
        ):
            token = (
                get_jwt_service()
                .create_access_token(
                    user_id="test-user",
                    organization_id="test-org",
                )
            )

            headers = {
                "Authorization": f"Bearer {token}",
            }

            # Public endpoint: no token required.
            health_response = client.get(
                "/api/v1/health"
            )

            assert health_response.status_code == 200

            assert (
                health_response.json()["status"]
                == "healthy"
            )

            # Protected endpoint without a token.
            missing_token_response = client.post(
                "/api/v1/rag/query",
                json={
                    "knowledge_base_id": "test-kb",
                    "query": "What is recommended?",
                    "k": 3,
                },
            )

            assert (
                missing_token_response.status_code
                == 401
            )

            assert (
                missing_token_response.json()[
                    "error"
                ]["code"]
                == "AUTHENTICATION_ERROR"
            )

            assert (
                missing_token_response.headers.get(
                    "www-authenticate"
                )
                == "Bearer"
            )

            # Protected endpoint with an invalid token.
            invalid_token_response = client.post(
                "/api/v1/rag/query",
                headers={
                    "Authorization": (
                        "Bearer invalid-token"
                    ),
                },
                json={
                    "knowledge_base_id": "test-kb",
                    "query": "What is recommended?",
                    "k": 3,
                },
            )

            assert (
                invalid_token_response.status_code
                == 401
            )

            assert (
                invalid_token_response.json()[
                    "error"
                ]["code"]
                == "AUTHENTICATION_ERROR"
            )

            # Valid authenticated PDF upload.
            upload_response = client.post(
                "/api/v1/documents",
                headers=headers,
                data={
                    "knowledge_base_id": "test-kb",
                },
                files={
                    "file": (
                        "test.pdf",
                        b"%PDF-1.4 fake test content",
                        "application/pdf",
                    )
                },
            )

            assert upload_response.status_code == 201

            upload_body = upload_response.json()

            assert (
                upload_body["document_id"]
                == "document-123"
            )

            assert upload_body["chunk_count"] == 3
            assert upload_body["vector_count"] == 3

            # Valid authenticated RAG query.
            query_response = client.post(
                "/api/v1/rag/query",
                headers=headers,
                json={
                    "knowledge_base_id": "test-kb",
                    "query": (
                        "What lifestyle changes "
                        "are recommended?"
                    ),
                    "k": 3,
                    "document_id": "document-123",
                },
            )

            assert query_response.status_code == 200

            query_body = query_response.json()

            assert query_body["grounded"] is True

            assert query_body["citations"] == [
                "S1"
            ]

            assert len(query_body["sources"]) == 1

            assert "[S1]" in query_body["answer"]

            # Invalid file-type protection.
            invalid_upload_response = client.post(
                "/api/v1/documents",
                headers=headers,
                data={
                    "knowledge_base_id": "test-kb",
                },
                files={
                    "file": (
                        "test.txt",
                        b"not a pdf",
                        "text/plain",
                    )
                },
            )

            assert (
                invalid_upload_response.status_code
                == 422
            )

            print(
                "\n=== FASTAPI ENDPOINT TEST ==="
            )

            print(
                "Health:",
                health_response.json(),
            )

            print(
                "Missing-token protection confirmed."
            )

            print(
                "Invalid-token protection confirmed."
            )

            print(
                "Active membership and role "
                "authorization confirmed."
            )

            print(
                "Upload document:",
                upload_body["document_id"],
            )

            print(
                "RAG answer:",
                query_body["answer"],
            )

            print(
                "Invalid PDF protection confirmed."
            )

            print(
                "FastAPI endpoint test "
                "passed successfully."
            )

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    main()


# Run:
# uv run python -m tests.test_api_endpoints
# uv run python -m tests.test_jwt_auth
