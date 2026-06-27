
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_db_session,
    get_shared_embedding_provider,
    get_shared_llm_provider,
    require_organization_roles,
)
from backend.app.api.schemas import (
    DocumentUploadResponse,
    HealthResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSourceResponse,
)
from backend.app.auth.roles import OrganizationRole
from backend.app.core.config import settings
from backend.app.core.exceptions import InvalidUploadError
from backend.app.database.repositories import (
    DocumentRepository,
)
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
)
from backend.app.generation import (
    GroundedAnswerService,
)
from backend.app.ingestion.loaders.pdf_loader import (
    PDFDocumentLoader,
)
from backend.app.ingestion.parsers.pdf_parser import (
    PDFDocumentParser,
)
from backend.app.ingestion.processors.chunker import (
    DocumentChunker,
)
from backend.app.ingestion.processors.text_cleaner import (
    TextCleaner,
)
from backend.app.llms.base import BaseLLMProvider
from backend.app.rate_limiting.dependencies import (
    require_user_rate_limit,
)
from backend.app.retrieval import RetrievalService
from backend.app.services.document_ingestion import (
    DocumentIngestionService,
)
from backend.app.services.rag_query import (
    RAGQueryService,
)
from backend.app.vectorstores.factory import (
    get_vector_store,
)


router = APIRouter()


require_document_write_access = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
    )
)


require_document_read_access = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
        OrganizationRole.VIEWER,
    )
)


upload_rate_limit = require_user_rate_limit(
    scope="document-upload",
    limit=settings.rate_limit_upload_requests,
    window_seconds=(
        settings.rate_limit_upload_window_seconds
    ),
)


rag_query_rate_limit = require_user_rate_limit(
    scope="rag-query",
    limit=settings.rate_limit_rag_requests,
    window_seconds=(
        settings.rate_limit_rag_window_seconds
    ),
)


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Return basic application health information."""

    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        environment=settings.app_environment,
    )


async def _save_pdf_upload(
    *,
    upload: UploadFile,
    destination: Path,
) -> int:
    """Save an uploaded PDF while enforcing the size limit."""

    suffix = Path(
        upload.filename or ""
    ).suffix.lower()

    if (
        suffix != ".pdf"
        and upload.content_type != "application/pdf"
    ):
        raise InvalidUploadError(
            message="Only PDF documents are accepted.",
            details={
                "filename": upload.filename,
                "content_type": upload.content_type,
            },
        )

    total_bytes = 0
    read_size = 1024 * 1024

    try:
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload.read(read_size)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > settings.upload_max_bytes:
                    raise InvalidUploadError(
                        message=(
                            "The uploaded PDF exceeds the "
                            "maximum permitted size."
                        ),
                        details={
                            "maximum_bytes": (
                                settings.upload_max_bytes
                            ),
                        },
                    )

                output_file.write(chunk)

    finally:
        await upload.close()

    if total_bytes == 0:
        raise InvalidUploadError(
            message="The uploaded PDF is empty."
        )

    return total_bytes


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
    dependencies=[
        Depends(upload_rate_limit),
    ],
)
async def upload_document(
    access: Annotated[
        OrganizationAccess,
        Depends(require_document_write_access),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
    embedding_provider: Annotated[
        BaseEmbeddingProvider,
        Depends(get_shared_embedding_provider),
    ],
    knowledge_base_id: Annotated[
        str,
        Form(min_length=1, max_length=128),
    ],
    file: Annotated[
        UploadFile,
        File(...),
    ],
) -> DocumentUploadResponse:
    """Upload and ingest one PDF document."""

    normalized_knowledge_base_id = (
        knowledge_base_id.strip()
    )

    if not normalized_knowledge_base_id:
        raise InvalidUploadError(
            message=(
                "knowledge_base_id cannot be empty."
            )
        )

    vector_store = get_vector_store(
        embedding_provider,
        organization_id=access.organization_id,
        user_id=access.user_id,
        knowledge_base_id=(
            normalized_knowledge_base_id
        ),
    )

    try:
        with TemporaryDirectory(
            prefix="rag_upload_"
        ) as temporary_directory:
            safe_filename = Path(
                file.filename or "document.pdf"
            ).name

            temporary_path = (
                Path(temporary_directory)
                / safe_filename
            )

            await _save_pdf_upload(
                upload=file,
                destination=temporary_path,
            )

            repository = DocumentRepository(session)

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
                or settings.embedding_model_name
            )

            embedding_dimension = getattr(
                embedding_provider,
                "embedding_dimension",
                None,
            )

            if not isinstance(
                embedding_dimension,
                int,
            ):
                embedding_dimension = None

            ingestion_service = (
                DocumentIngestionService(
                    session=session,
                    repository=repository,
                    loader=PDFDocumentLoader(),
                    parser=PDFDocumentParser(),
                    cleaner=TextCleaner(),
                    chunker=DocumentChunker(),
                    vector_store=vector_store,
                    embedding_provider_name=(
                        type(
                            embedding_provider
                        ).__name__
                    ),
                    embedding_model_name=(
                        embedding_model_name
                    ),
                    embedding_dimension=(
                        embedding_dimension
                    ),
                    vector_store_provider_name=(
                        type(vector_store).__name__
                    ),
                )
            )

            result = (
                await ingestion_service.ingest_pdf(
                    file_path=temporary_path,
                    organization_id=(
                        access.organization_id
                    ),
                    user_id=access.user_id,
                    knowledge_base_id=(
                        normalized_knowledge_base_id
                    ),
                )
            )

            return DocumentUploadResponse(
                document_id=result.document_id,
                status=result.status,
                filename=(
                    file.filename or "document.pdf"
                ),
                total_pages=result.total_pages,
                chunk_count=result.chunk_count,
                vector_count=len(result.vector_ids),
            )

    finally:
        await asyncio.to_thread(
            vector_store.close,
        )


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    tags=["RAG"],
    dependencies=[
        Depends(rag_query_rate_limit),
    ],
)
async def query_documents(
    request: RAGQueryRequest,
    access: Annotated[
        OrganizationAccess,
        Depends(require_document_read_access),
    ],
    embedding_provider: Annotated[
        BaseEmbeddingProvider,
        Depends(get_shared_embedding_provider),
    ],
    llm_provider: Annotated[
        BaseLLMProvider,
        Depends(get_shared_llm_provider),
    ],
) -> RAGQueryResponse:
    """Answer one question from the scoped knowledge base."""

    vector_store = get_vector_store(
        embedding_provider,
        organization_id=access.organization_id,
        user_id=access.user_id,
        knowledge_base_id=request.knowledge_base_id,
    )

    try:
        retrieval_service = RetrievalService(
            vector_store=vector_store,
            default_k=settings.retrieval_top_k,
            max_k=20,
        )

        generation_service = (
            GroundedAnswerService(
                llm_provider=llm_provider,
                max_context_characters=24_000,
            )
        )

        rag_service = RAGQueryService(
            retrieval_service=retrieval_service,
            generation_service=generation_service,
        )

        result = await rag_service.answer(
            query=request.query,
            k=request.k,
            document_id=request.document_id,
        )

        return RAGQueryResponse(
            query=result.query,
            answer=result.answer,
            grounded=result.grounded,
            citations=list(result.citations),
            sources=[
                RAGSourceResponse(
                    citation_id=source.citation_id,
                    document_id=source.document_id,
                    chunk_id=source.chunk_id,
                    filename=source.filename,
                    page_number=source.page_number,
                )
                for source in result.sources
            ],
            retrieved_chunk_count=(
                result.retrieved_chunk_count
            ),
        )

    finally:
        await asyncio.to_thread(
            vector_store.close,
        )
