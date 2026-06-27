
import asyncio
from hashlib import sha256
from uuid import uuid4

from backend.app.database.enums import (
    DocumentStatus,
)
from backend.app.database.repositories import (
    ChunkReference,
    DocumentRepository,
)
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)
from backend.app.services.document_management import (
    DocumentManagementService,
)


class FakeVectorStore:
    """Record vector IDs deleted by the service."""

    def __init__(self) -> None:
        self.deleted_ids: list[str] = []

    def delete_chunks(
        self,
        chunk_ids: list[str],
    ) -> None:
        self.deleted_ids.extend(chunk_ids)


async def main() -> None:
    unique_value = uuid4().hex

    organization_id = (
        f"document-management-org-"
        f"{unique_value[:8]}"
    )

    user_id = (
        f"document-management-user-"
        f"{unique_value[8:16]}"
    )

    knowledge_base_id = (
        f"document-management-kb-"
        f"{unique_value[16:24]}"
    )

    file_hash = sha256(
        unique_value.encode("utf-8")
    ).hexdigest()

    chunk_id = sha256(
        f"chunk-{unique_value}".encode("utf-8")
    ).hexdigest()

    vector_id = sha256(
        (
            f"{organization_id}:"
            f"{user_id}:"
            f"{knowledge_base_id}:"
            f"{chunk_id}"
        ).encode("utf-8")
    ).hexdigest()

    session_factory = get_session_factory()

    document_id: str | None = None

    try:
        async with session_factory() as session:
            repository = DocumentRepository(session)

            document = await repository.create_document(
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                filename="management-test.pdf",
                file_hash=file_hash,
                file_size_bytes=1024,
                total_pages=3,
            )

            document_id = document.id

            await repository.add_chunk_references(
                document_id=document.id,
                organization_id=organization_id,
                user_id=user_id,
                chunk_references=[
                    ChunkReference(
                        chunk_id=chunk_id,
                        vector_id=vector_id,
                        page_number=1,
                        chunk_index=0,
                    )
                ],
            )

            await repository.update_status(
                document_id=document.id,
                organization_id=organization_id,
                user_id=user_id,
                status=DocumentStatus.COMPLETED,
                embedding_provider="huggingface",
                embedding_model=(
                    "sentence-transformers/"
                    "all-MiniLM-L6-v2"
                ),
                embedding_dimension=384,
                vector_store_provider="chroma",
                total_pages=3,
            )

            await session.commit()

        fake_vector_store = FakeVectorStore()

        async with session_factory() as session:
            service = DocumentManagementService(
                session=session,
                repository=DocumentRepository(session),
            )

            listed = await service.list_documents(
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                offset=0,
                limit=50,
            )

            assert listed.total == 1
            assert len(listed.documents) == 1
            assert (
                listed.documents[0].id
                == document_id
            )

            detail = await service.get_document(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
            )

            assert detail.filename == (
                "management-test.pdf"
            )

            assert detail.status == (
                DocumentStatus.COMPLETED.value
            )

            assert detail.chunk_count == 1

            await service.delete_document(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                vector_store=fake_vector_store,
            )

            assert fake_vector_store.deleted_ids == [
                vector_id
            ]

            deleted = (
                await DocumentRepository(session)
                .get_by_id(
                    document_id=document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )
            )

            assert deleted is None

            print(
                "\n=== DOCUMENT MANAGEMENT TEST ==="
            )
            print("Document listing confirmed.")
            print("Document total count confirmed.")
            print("Document detail confirmed.")
            print("Chroma vector deletion confirmed.")
            print("MySQL deletion confirmed.")
            print(
                "Document management test "
                "passed successfully."
            )

            document_id = None

    finally:
        if document_id is not None:
            async with session_factory() as cleanup:
                await DocumentRepository(
                    cleanup
                ).delete_document_record(
                    document_id=document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                await cleanup.commit()

        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())


# uv run python -m tests.test_document_management