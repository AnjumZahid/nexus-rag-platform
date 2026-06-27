import asyncio
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_db_session,
    get_shared_embedding_provider,
    require_organization_roles,
)
from backend.app.api.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
)
from backend.app.auth.roles import (
    OrganizationRole,
)
from backend.app.database.repositories import (
    DocumentRepository,
)
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
)
from backend.app.services.document_management import (
    DocumentManagementService,
    DocumentView,
)
from backend.app.vectorstores.factory import (
    get_vector_store,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


require_document_read_access = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
        OrganizationRole.VIEWER,
    )
)


require_document_delete_access = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
    )
)


def build_document_response(
    document: DocumentView,
) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        knowledge_base_id=(
            document.knowledge_base_id
        ),
        filename=document.filename,
        status=document.status,
        file_size_bytes=document.file_size_bytes,
        total_pages=document.total_pages,
        chunk_count=document.chunk_count,
        embedding_provider=(
            document.embedding_provider
        ),
        embedding_model=document.embedding_model,
        embedding_dimension=(
            document.embedding_dimension
        ),
        vector_store_provider=(
            document.vector_store_provider
        ),
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def build_document_service(
    session: AsyncSession,
) -> DocumentManagementService:
    return DocumentManagementService(
        session=session,
        repository=DocumentRepository(session),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
)
async def list_documents(
    access: Annotated[
        OrganizationAccess,
        Depends(require_document_read_access),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
    knowledge_base_id: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=128,
        ),
    ] = None,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 50,
) -> DocumentListResponse:
    result = await build_document_service(
        session
    ).list_documents(
        organization_id=access.organization_id,
        user_id=access.user_id,
        knowledge_base_id=knowledge_base_id,
        offset=offset,
        limit=limit,
    )

    return DocumentListResponse(
        documents=[
            build_document_response(document)
            for document in result.documents
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: str,
    access: Annotated[
        OrganizationAccess,
        Depends(require_document_read_access),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> DocumentResponse:
    document = await build_document_service(
        session
    ).get_document(
        document_id=document_id,
        organization_id=access.organization_id,
        user_id=access.user_id,
    )

    return build_document_response(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: str,
    access: Annotated[
        OrganizationAccess,
        Depends(require_document_delete_access),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
    embedding_provider: Annotated[
        BaseEmbeddingProvider,
        Depends(get_shared_embedding_provider),
    ],
) -> Response:
    service = build_document_service(session)

    document = await service.get_document(
        document_id=document_id,
        organization_id=access.organization_id,
        user_id=access.user_id,
    )

    vector_store = get_vector_store(
        embedding_provider,
        organization_id=access.organization_id,
        user_id=access.user_id,
        knowledge_base_id=(
            document.knowledge_base_id
        ),
    )

    try:
        await service.delete_document(
            document_id=document_id,
            organization_id=access.organization_id,
            user_id=access.user_id,
            vector_store=vector_store,
        )

    finally:
        await asyncio.to_thread(
            vector_store.close,
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )