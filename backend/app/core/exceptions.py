from typing import Any


class AppError(Exception):
    """Base exception for controlled application errors."""

    code: str = "APPLICATION_ERROR"
    default_message: str = "An application error occurred."
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(AppError):
    code = "CONFIGURATION_ERROR"
    default_message = "The application configuration is invalid."
    status_code = 500


class DocumentError(AppError):
    code = "DOCUMENT_ERROR"
    default_message = "The document could not be processed."
    status_code = 422


class DocumentNotFoundError(DocumentError):
    code = "DOCUMENT_NOT_FOUND"
    default_message = "The requested document was not found."
    status_code = 404


class UnsupportedDocumentTypeError(DocumentError):
    code = "UNSUPPORTED_DOCUMENT_TYPE"
    default_message = "The document type is not supported."
    status_code = 415


class DocumentParsingError(DocumentError):
    code = "DOCUMENT_PARSING_FAILED"
    default_message = "The document content could not be extracted."
    status_code = 422


# note: Add this class after creating text_cleaner.py in processors
class DocumentChunkingError(DocumentError):
    code = "DOCUMENT_CHUNKING_FAILED"
    default_message = "The document text could not be split into chunks."
    status_code = 422

# note: Add this class after creating chunker.py in processors
class DocumentMetadataError(DocumentError):
    code = "DOCUMENT_METADATA_FAILED"
    default_message = "Document metadata could not be prepared."
    status_code = 422

# note: Add this class after creating huggingface.py in backend/app/embeddings
class EmbeddingError(AppError):
    code = "EMBEDDING_FAILED"
    default_message = "Text could not be converted into embeddings."
    status_code = 500

# note: Add this class after creating chroma_store.py in backend/app/vectorstores
class VectorStoreError(AppError):
    code = "VECTOR_STORE_ERROR"
    default_message = "The vector store operation failed."
    status_code = 500

# note: Add following after creating session.py in backend/app/database
class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    default_message = "A database operation failed."
    status_code = 500

# note: Add following after creating session.py in backend/app/database
class DatabaseConnectionError(DatabaseError):
    code = "DATABASE_CONNECTION_ERROR"
    default_message = "The application could not connect to the database."
    status_code = 503


# note: Add following after creating enums.py & backend/app/database/repositories/document_repository.py in backend/app/database
# Add to backend/app/core/exceptions.py


class DuplicateDocumentError(AppError):
    code = "DUPLICATE_DOCUMENT"
    default_message = (
        "This document has already been uploaded "
        "to the selected knowledge base."
    )
    status_code = 409


class DocumentNotFoundError(AppError):
    code = "DOCUMENT_NOT_FOUND"
    default_message = "The requested document was not found."
    status_code = 404

# note: Add following with "backend/app/services/document_ingestion.py"
class DocumentIngestionError(AppError):
    code = "DOCUMENT_INGESTION_ERROR"
    default_message = "The document could not be ingested."
    status_code = 500

# note: Add following with backend/app/retrieval/service.py"
class InvalidQueryError(AppError):
    code = "INVALID_QUERY"
    default_message = "The retrieval query is invalid."
    status_code = 422


class RetrievalError(AppError):
    code = "RETRIEVAL_ERROR"
    default_message = "Relevant document context could not be retrieved."
    status_code = 500


# note: Add following with "backend/app/generation/prompts.py" and backend/app/generation/service.py"
class GenerationError(AppError):
    code = "GENERATION_ERROR"
    default_message = "A grounded answer could not be generated."
    status_code = 500

# # note: Add following with New-Item -ItemType File -Force "backend/app/llms/base.py"
# New-Item -ItemType File -Force "backend/app/llms/openai_provider.py"

class LLMProviderError(AppError):
    code = "LLM_PROVIDER_ERROR"
    default_message = "The language-model provider request failed."
    status_code = 503

    # add fol with New-Item -ItemType File -Force "backend/app/llms/base.py"
    # New-Item -ItemType File -Force "backend/app/llms/gemini_ai.py"

class LLMProviderError(AppError):
    code = "LLM_PROVIDER_ERROR"
    default_message = "The language-model provider request failed."
    status_code = 503

# add fol with New-Item -ItemType Directory -Force "backend/app/api"
class InvalidUploadError(AppError):
    code = "INVALID_UPLOAD"
    default_message = "The uploaded document is invalid."
    status_code = 422


# add fol with New-Item -ItemType Directory -Force "backend/app/auth"
class AuthenticationError(AppError):
    code = "AUTHENTICATION_ERROR"
    default_message = (
        "Valid authentication credentials are required."
    )
    status_code = 401

class AuthorizationError(AppError):
    code = "AUTHORIZATION_ERROR"
    default_message = (
        "You are not authorized to perform this action."
    )
    status_code = 403

class ConflictError(AppError):
    code = "RESOURCE_CONFLICT"
    default_message = (
        "The requested resource already exists."
    )
    status_code = 409

# add fol with New-Item -ItemType File -Force "backend\app\services\document_management.py
class DocumentDeletionError(AppError):
    code = "DOCUMENT_DELETION_ERROR"
    default_message = (
        "The document could not be deleted completely."
    )
    status_code = 500

# uv run python -c "from backend.app.core.exceptions import DocumentNotFoundError; error = DocumentNotFoundError(details={'path': 'docs/sample.pdf'}); print(error.code); print(error.status_code); print(error); print(error.details)"