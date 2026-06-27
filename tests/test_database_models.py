from backend.app.database.base import Base
from backend.app.database.models import (
    DocumentChunkRecord,
    DocumentRecord,
)


def main() -> None:
    table_names = sorted(Base.metadata.tables.keys())

    print("\n=== DATABASE MODEL TEST ===")
    print("Registered tables:", table_names)

    print("\nDocument columns:")
    for column in DocumentRecord.__table__.columns:
        print("-", column.name, column.type)

    print("\nChunk columns:")
    for column in DocumentChunkRecord.__table__.columns:
        print("-", column.name, column.type)

    assert "document_records" in table_names
    assert "document_chunk_records" in table_names
    assert "file_hash" in DocumentRecord.__table__.columns
    assert "chunk_id" in DocumentChunkRecord.__table__.columns

    print("\nDatabase model test passed successfully.")


if __name__ == "__main__":
    main()

# uv run python -m tests.test_database_models