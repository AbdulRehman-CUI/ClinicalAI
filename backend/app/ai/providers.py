"""Provider abstractions for AI model backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import Settings, get_settings
import logging
import json

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - handled during dependency installation
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled during dependency installation
    OpenAI = None  # type: ignore[assignment]


class BaseAIProvider(ABC):
    """Abstract interface for AI backends used by the analysis pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @abstractmethod
    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return the raw text response generated from the supplied prompts."""


class OpenAIProvider(BaseAIProvider):
    """Use OpenAI's Responses API for AI analysis generation."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        super().__init__(settings=settings)
        self.client = client

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.settings.openai_api_key:
            raise RuntimeError("OpenAI API key is not configured.")
        if OpenAI is None:
            raise RuntimeError("The OpenAI SDK is not available.")
        return OpenAI(api_key=self.settings.openai_api_key)

    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()
        response = client.responses.create(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.settings.openai_temperature,
            timeout=self.settings.openai_timeout,
            max_output_tokens=self.settings.max_ai_tokens,
        )
        return getattr(response, "output_text", "") or ""


class GeminiProvider(BaseAIProvider):
    """Use Google's Gemini API for AI analysis generation."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        super().__init__(settings=settings)
        self.client = client

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.settings.gemini_api_key:
            raise RuntimeError("Gemini API key is not configured.")
        if genai is None:
            raise RuntimeError("The Google GenAI SDK is not available.")
        return genai.Client(api_key=self.settings.gemini_api_key)

    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()

        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                systemInstruction=system_prompt,
                temperature=self.settings.openai_temperature,
                maxOutputTokens=self.settings.max_ai_tokens,
            ),
        )

        logger = logging.getLogger(__name__)

        # Log raw SDK response for debugging compatibility differences
        try:
            # Attempt to serialize common response shapes
            serialized = None
            # If SDK response exposes a json-like dict
            if hasattr(response, "to_dict") and callable(getattr(response, "to_dict")):
                serialized = response.to_dict()
            else:
                # Collect common attributes
                candidate_attrs = [
                    "text",
                    "candidates",
                    "content",
                    "outputs",
                    "output",
                    "response",
                    "raw",
                ]
                info = {}
                for attr in candidate_attrs:
                    if hasattr(response, attr):
                        try:
                            val = getattr(response, attr)
                            info[attr] = val
                        except Exception:
                            info[attr] = repr(getattr(response, attr))
                # Also include a repr and dir for full visibility
                info["repr"] = repr(response)
                info["dir"] = [a for a in dir(response) if not a.startswith("__")]
                serialized = info
            try:
                logger.debug("Raw Gemini SDK response: %s", json.dumps(serialized, default=str, ensure_ascii=False))
            except Exception:
                logger.debug("Raw Gemini SDK response (repr): %s", repr(serialized))
        except Exception:
            logger.exception("Failed to serialize Gemini SDK response for logging.")

        return getattr(response, "text", "") or ""


def build_ai_provider(settings: Settings | None = None, client: Any | None = None) -> BaseAIProvider:
    """Instantiate the configured AI provider based on application settings."""
    resolved_settings = settings or get_settings()
    provider_name = (resolved_settings.ai_provider or "openai").strip().lower()
    print("AI Provider:", resolved_settings.ai_provider)
    print("Gemini Model:", resolved_settings.gemini_model)
    print("Gemini Key:", resolved_settings.gemini_api_key[:10] if resolved_settings.gemini_api_key else None)
    if provider_name == "gemini":
        return GeminiProvider(settings=resolved_settings, client=client)
    return OpenAIProvider(settings=resolved_settings, client=client)
