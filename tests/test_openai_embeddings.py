from backend.app.embeddings.factory import get_embedding_provider


def main() -> None:
    provider = get_embedding_provider()

    document_texts = [
        "High blood pressure can damage the heart.",
        "Regular exercise supports cardiovascular health.",
    ]

    query = "How does blood pressure affect the heart?"

    document_vectors = provider.embed_documents(document_texts)
    query_vector = provider.embed_query(query)

    print("\n=== OPENAI EMBEDDING TEST ===")
    print("Provider:", provider.provider_name)
    print("Model:", provider.model_name)
    print("Document vectors:", len(document_vectors))
    print("Document vector dimension:", len(document_vectors[0]))
    print("Query vector dimension:", len(query_vector))

    assert provider.provider_name == "openai"
    assert len(document_vectors) == 2
    assert len(document_vectors[0]) == len(query_vector)

    print("\nOpenAI embedding test passed successfully.")


if __name__ == "__main__":
    main()


# uv run python -m tests.test_openai_embeddings