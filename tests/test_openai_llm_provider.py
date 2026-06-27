### `tests/test_openai_llm_provider.py`

from backend.app.core.exceptions import AppError
from backend.app.llms import get_llm_provider


def main() -> None:
    try:
        provider = get_llm_provider()

        result = provider.generate(
            system_prompt=(
                "You are a concise test assistant. "
                "Follow the user instruction exactly."
            ),
            user_prompt=(
                "Return one short sentence confirming "
                "that the LLM provider works."
            ),
        )

        assert isinstance(result, str)
        assert result.strip()

        print("\n=== OPENAI LLM PROVIDER TEST ===")
        print("Provider:", type(provider).__name__)
        print(
            "Model:",
            getattr(provider, "model_name", "unknown"),
        )
        print("Response:", result)
        print(
            "OpenAI LLM provider test "
            "passed successfully."
        )

    except AppError as exc:
        print("\nOpenAI LLM provider test failed.")
        print("Code:", exc.code)
        print("Message:", exc.message)

        if exc.details:
            print("Details:", exc.details)

        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()


# uv run python -m tests.test_openai_llm_provider