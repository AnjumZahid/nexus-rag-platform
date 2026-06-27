
import asyncio

from backend.app.core.exceptions import GenerationError
from backend.app.generation import GroundedAnswerService
from backend.app.generation.prompts import (
    GROUNDING_SYSTEM_PROMPT,
)
from backend.app.retrieval import (
    RetrievalResult,
    RetrievedChunk,
)


class GroupedCitationProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return (
            "The first and third sources support this claim "
            "[S1, S3]. The first source also supports the "
            "second claim [S1]."
        )


class InvalidGroupedCitationProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return (
            "This contains one valid and one invented source "
            "[S1, S99]."
        )


class SecretFailureProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        raise RuntimeError(
            "x-goog-api-key: SUPER-SECRET-TEST-KEY"
        )


def build_retrieval_result() -> RetrievalResult:
    chunks = tuple(
        RetrievedChunk(
            citation_id=f"S{index}",
            rank=index,
            content=f"Evidence from source {index}.",
            document_id="document-123",
            chunk_id=f"chunk-{index}",
            filename="guidelines.pdf",
            page_number=index,
            metadata={
                "document_id": "document-123",
                "chunk_id": f"chunk-{index}",
            },
        )
        for index in range(1, 4)
    )

    context = "\n\n".join(
        (
            f"[{chunk.citation_id}] "
            f"| file={chunk.filename} "
            f"| page={chunk.page_number}\n"
            f"{chunk.content}"
        )
        for chunk in chunks
    )

    return RetrievalResult(
        query="What do the documents recommend?",
        chunks=chunks,
        context=context,
    )


async def main() -> None:
    retrieval_result = build_retrieval_result()

    grouped_service = GroundedAnswerService(
        llm_provider=GroupedCitationProvider(),
    )

    grouped_result = await grouped_service.generate(
        retrieval_result=retrieval_result,
    )

    assert grouped_result.citations == (
        "S1",
        "S3",
    )

    assert tuple(
        source.citation_id
        for source in grouped_result.sources
    ) == (
        "S1",
        "S3",
    )

    invalid_service = GroundedAnswerService(
        llm_provider=InvalidGroupedCitationProvider(),
    )

    invalid_citation_detected = False

    try:
        await invalid_service.generate(
            retrieval_result=retrieval_result,
        )
    except GenerationError:
        invalid_citation_detected = True

    assert invalid_citation_detected is True

    secret_service = GroundedAnswerService(
        llm_provider=SecretFailureProvider(),
    )

    secret_protected = False

    try:
        await secret_service.generate(
            retrieval_result=retrieval_result,
        )
    except GenerationError as exc:
        visible_error = (
            f"{exc} "
            f"{exc.details} "
            f"{exc.__cause__}"
        )

        assert (
            "SUPER-SECRET-TEST-KEY"
            not in visible_error
        )

        assert exc.__cause__ is None

        secret_protected = True

    assert secret_protected is True

    assert (
        "never combine them as [S1, S2]"
        in GROUNDING_SYSTEM_PROMPT
    )

    print("\n=== GENERATION HARDENING TEST ===")
    print(
        "Grouped citations:",
        grouped_result.citations,
    )
    print("Grouped-citation parsing confirmed.")
    print("Invalid grouped citation rejected.")
    print("Provider secret protection confirmed.")
    print("Separate-citation prompt rule confirmed.")
    print(
        "Generation hardening test "
        "passed successfully."
    )


if __name__ == "__main__":
    asyncio.run(main())
