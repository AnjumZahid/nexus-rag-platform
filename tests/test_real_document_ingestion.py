import asyncio
from pathlib import Path
from uuid import uuid4

from backend.app.database.repositories import DocumentRepository
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)
from backend.app.embeddings.factory import get_embedding_provider
from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader
from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser
from backend.app.ingestion.processors.chunker import DocumentChunker
from backend.app.ingestion.processors.text_cleaner import TextCleaner
from backend.app.services import DocumentIngestionService
from backend.app.vectorstores.factory import get_vector_store


async def main() -> None:
    pdf_path = Path(
        "docs/who_pen_guidelines.pdf"
    ).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Real test PDF was not found: {pdf_path}"
        )

    unique_value = uuid4().hex

    organization_id = f"real-org-{unique_value[:8]}"
    user_id = f"real-user-{unique_value[8:16]}"
    knowledge_base_id = f"real-kb-{unique_value[16:24]}"

    session_factory = get_session_factory()

    vector_store = None
    ingestion_result = None
    vectors_deleted = False
    database_record_deleted = False

    try:
        embedding_provider = get_embedding_provider()

        vector_store = get_vector_store(
            embedding_provider,
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )

        embedding_model_name = str(
            getattr(
                embedding_provider,
                "model_name",
                None,
            )
            or getattr(
                embedding_provider,
                "_model_name",
                None,
            )
            or "configured-embedding-model"
        )

        async with session_factory() as session:
            repository = DocumentRepository(session)

            service = DocumentIngestionService(
                session=session,
                repository=repository,
                loader=PDFDocumentLoader(),
                parser=PDFDocumentParser(),
                cleaner=TextCleaner(),
                chunker=DocumentChunker(),
                vector_store=vector_store,
                embedding_provider_name=(
                    type(embedding_provider).__name__
                ),
                embedding_model_name=embedding_model_name,
                vector_store_provider_name=(
                    type(vector_store).__name__
                ),
            )

            print(
                "\nStarting real PDF ingestion:",
                pdf_path.name,
            )

            ingestion_result = await service.ingest_pdf(
                file_path=pdf_path,
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
            )

            assert ingestion_result.status == "completed"
            assert ingestion_result.total_pages > 0
            assert ingestion_result.chunk_count > 0
            assert len(
                ingestion_result.vector_ids
            ) == ingestion_result.chunk_count

            stored_document = await repository.get_by_id(
                document_id=ingestion_result.document_id,
                organization_id=organization_id,
                user_id=user_id,
            )

            assert stored_document is not None
            assert stored_document.status == "completed"
            assert (
                stored_document.chunk_count
                == ingestion_result.chunk_count
            )

            search_results = await asyncio.to_thread(
                vector_store.similarity_search,
                "What treatment is recommended for high blood pressure?",
                k=3,
            )

            assert search_results

            for document in search_results:
                assert (
                    document.metadata.get("organization_id")
                    == organization_id
                )
                assert (
                    document.metadata.get("user_id")
                    == user_id
                )
                assert (
                    document.metadata.get("knowledge_base_id")
                    == knowledge_base_id
                )

            print(
                "\n=== REAL DOCUMENT INGESTION TEST ==="
            )
            print(
                "Document ID:",
                ingestion_result.document_id,
            )
            print(
                "Status:",
                ingestion_result.status,
            )
            print(
                "Pages:",
                ingestion_result.total_pages,
            )
            print(
                "Chunks:",
                ingestion_result.chunk_count,
            )
            print(
                "Vectors:",
                len(ingestion_result.vector_ids),
            )
            print(
                "Retrieved documents:",
                len(search_results),
            )

            first_result = search_results[0]

            preview = " ".join(
                first_result.page_content.split()
            )[:300]

            print(
                "Top result preview:",
                preview,
            )

            # Delete Chroma vectors before deleting MySQL references.
            await asyncio.to_thread(
                vector_store.delete_chunks,
                list(ingestion_result.vector_ids),
            )

            vectors_deleted = True

            deleted = await repository.delete_document_record(
                document_id=ingestion_result.document_id,
                organization_id=organization_id,
                user_id=user_id,
            )

            assert deleted is True

            await session.commit()

            database_record_deleted = True

            print("Real Chroma vectors deleted.")
            print("Temporary MySQL record deleted.")
            print(
                "Real document ingestion test "
                "passed successfully."
            )

    finally:
        if (
            ingestion_result is not None
            and vector_store is not None
            and not vectors_deleted
        ):
            try:
                await asyncio.to_thread(
                    vector_store.delete_chunks,
                    list(ingestion_result.vector_ids),
                )
            except Exception as cleanup_error:
                print(
                    "Vector cleanup warning:",
                    type(cleanup_error).__name__,
                    str(cleanup_error),
                )

        if not database_record_deleted:
            try:
                async with session_factory() as cleanup_session:
                    cleanup_repository = DocumentRepository(
                        cleanup_session
                    )

                    test_documents = (
                        await cleanup_repository.list_documents(
                            organization_id=organization_id,
                            user_id=user_id,
                            knowledge_base_id=knowledge_base_id,
                        )
                    )

                    for document in test_documents:
                        await cleanup_repository.delete_document_record(
                            document_id=document.id,
                            organization_id=organization_id,
                            user_id=user_id,
                        )

                    await cleanup_session.commit()

            except Exception as cleanup_error:
                print(
                    "Database cleanup warning:",
                    type(cleanup_error).__name__,
                    str(cleanup_error),
                )

        if vector_store is not None:
            try:
                await asyncio.to_thread(
                    vector_store.close,
                )
            except Exception as close_error:
                print(
                    "Vector-store close warning:",
                    type(close_error).__name__,
                    str(close_error),
                )

        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())


# uv run python -m tests.test_real_document_ingestion