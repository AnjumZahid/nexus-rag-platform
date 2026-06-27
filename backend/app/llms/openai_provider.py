
### `backend/app/llms/openai_provider.py`

from openai import OpenAI

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    ConfigurationError,
    LLMProviderError,
)
from backend.app.core.logging import get_logger
from backend.app.llms.base import BaseLLMProvider

logger = get_logger(__name__)


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI Responses API provider.

    The provider converts the application's common generate() interface
    into one OpenAI Responses API request.
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
    ) -> None:
        if settings.openai_api_key is None:
            raise ConfigurationError(
                message="OPENAI_API_KEY is missing from the environment."
            )

        self.model_name = (
            model_name
            or settings.openai_llm_model
        )

        self.client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.openai_llm_timeout_seconds,
            max_retries=settings.openai_llm_max_retries,
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate one text answer through the Responses API."""

        if not system_prompt.strip():
            raise LLMProviderError(
                message="The system prompt cannot be empty."
            )

        if not user_prompt.strip():
            raise LLMProviderError(
                message="The user prompt cannot be empty."
            )

        logger.info(
            "openai_generation_started",
            model=self.model_name,
            system_prompt_length=len(system_prompt),
            user_prompt_length=len(user_prompt),
        )

        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=system_prompt,
                input=user_prompt,
                reasoning={
                    "effort": (
                        settings.openai_llm_reasoning_effort
                    ),
                },
                max_output_tokens=(
                    settings.openai_llm_max_output_tokens
                ),
            )
        except Exception as exc:
            logger.exception(
                "openai_generation_failed",
                model=self.model_name,
                error_type=type(exc).__name__,
            )

            raise LLMProviderError(
                details={
                    "provider": "openai",
                    "model": self.model_name,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            ) from exc

        output_text = response.output_text

        if not isinstance(output_text, str):
            raise LLMProviderError(
                message="OpenAI returned a non-text response.",
                details={
                    "provider": "openai",
                    "model": self.model_name,
                },
            )

        normalized_output = output_text.strip()

        if not normalized_output:
            raise LLMProviderError(
                message="OpenAI returned an empty response.",
                details={
                    "provider": "openai",
                    "model": self.model_name,
                },
            )

        logger.info(
            "openai_generation_completed",
            model=self.model_name,
            output_length=len(normalized_output),
        )

        return normalized_output

