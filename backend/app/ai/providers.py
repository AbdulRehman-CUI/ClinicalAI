"""Provider abstractions for AI model backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.services.exceptions import LLMRequestError

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

    def __init__(self, model: str, api_key: str, *, settings: Settings | None = None, client: Any = None) -> None:
        self.settings = settings or get_settings()
        self.model = model
        self.api_key = api_key
        self.client = client

    @abstractmethod
    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return the raw text response generated from the supplied prompts."""

    @abstractmethod
    def test_connection(self) -> None:
        """Make a small model request without clinical data."""


class OpenAIProvider(BaseAIProvider):
    """Use OpenAI's Responses API for AI analysis generation."""

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        if OpenAI is None:
            raise RuntimeError("The OpenAI SDK is not available.")
        return OpenAI(api_key=self.api_key, base_url="https://api.openai.com/v1", max_retries=0)

    def test_connection(self) -> None:
        self._get_client().responses.create(
            model=self.model, input="Reply OK.", max_output_tokens=16, timeout=12, store=False,
        )

    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.settings.openai_temperature,
            timeout=self.settings.openai_timeout,
            max_output_tokens=self.settings.max_ai_tokens,
            store=False,
        )
        return getattr(response, "output_text", "") or ""


class GeminiProvider(BaseAIProvider):
    """Use Google's Gemini API for AI analysis generation."""

    def _get_client(self, timeout: int | None = None) -> Any:
        if self.client is not None:
            return self.client
        if genai is None:
            raise RuntimeError("The Google GenAI SDK is not available.")
        return genai.Client(
            vertexai=False,
            api_key=self.api_key,
            http_options=types.HttpOptions(
                base_url="https://generativelanguage.googleapis.com",
                timeout=(timeout or self.settings.openai_timeout) * 1000,
            ),
        )

    def test_connection(self) -> None:
        self._get_client(timeout=12).models.generate_content(
            model=self.model, contents="Reply OK.",
            config=types.GenerateContentConfig(max_output_tokens=16),
        )

    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()

        response = client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                systemInstruction=system_prompt,
                temperature=self.settings.openai_temperature,
                maxOutputTokens=self.settings.max_ai_tokens,
            ),
        )

        return getattr(response, "text", "") or ""


PROVIDERS = {"openai": OpenAIProvider, "gemini": GeminiProvider}


def build_ai_provider(provider: str, model: str, api_key: str) -> BaseAIProvider:
    return PROVIDERS[provider](model, api_key)


def provider_error(exc: Exception) -> LLMRequestError:
    """Map SDK failures without returning provider bodies, URLs or headers."""
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    code = getattr(exc, "code", None)
    details = getattr(exc, "details", None)
    if isinstance(details, dict) and isinstance(details.get("error"), dict):
        reasons = {
            item["reason"] for item in details["error"].get("details") or []
            if isinstance(item, dict) and isinstance(item.get("reason"), str)
        }
    else:
        reasons = set()
    if code in ("insufficient_quota", "billing_hard_limit_reached") or status == 402 or "BILLING_DISABLED" in reasons:
        return LLMRequestError("llm_quota", "Your provider account has insufficient quota or credits.", 402)
    if status in (401, 403) or code == "invalid_api_key" or "API_KEY_INVALID" in reasons:
        return LLMRequestError("llm_invalid_key", "The provider rejected this API key or its permissions.", 422)
    if status in (400, 404):
        return LLMRequestError("llm_model_unavailable", "The selected model is unavailable to this key or rejected the request.", 422)
    if status == 429:
        return LLMRequestError("llm_rate_limited", "The provider is rate limiting this key. Try again later.", 429)
    if status in (408, 504) or isinstance(exc, (httpx.TimeoutException, TimeoutError)) or type(exc).__name__ == "APITimeoutError":
        return LLMRequestError("llm_timeout", "The provider request timed out.", 504)
    if isinstance(exc, (httpx.NetworkError, ConnectionError)) or type(exc).__name__ == "APIConnectionError":
        return LLMRequestError("llm_network", "Could not connect to the provider.", 503)
    return LLMRequestError("llm_unavailable", "The AI provider is temporarily unavailable.", 503)
