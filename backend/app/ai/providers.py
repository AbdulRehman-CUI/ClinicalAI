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

    def discover_models(self):
        return [m.id for m in self._get_client().models.list(timeout=12) if m.id.startswith(("gpt-", "o1", "o3", "o4")) and not any(x in m.id for x in ("audio", "realtime", "image", "transcribe", "search"))]

    def test_connection(self) -> None:
        response = self._get_client().responses.create(
            model=self.model, input="Reply OK.", max_output_tokens=256, timeout=12, store=False,
        )
        if not (getattr(response, "output_text", "") or "").strip():
            raise LLMRequestError("llm_empty_response", "The selected model returned no text. Try a different model.", 422)

    def generate_content(self, *, system_prompt: str, user_prompt: str) -> str:
        client = self._get_client()
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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

    def discover_models(self):
        return [m.name.removeprefix("models/") for m in self._get_client(timeout=12).models.list() if "generateContent" in (m.supported_actions or [])]

    def test_connection(self) -> None:
        response = self._get_client(timeout=12).models.generate_content(
            model=self.model, contents="Reply OK.",
            config=types.GenerateContentConfig(max_output_tokens=256),
        )
        if not (getattr(response, "text", "") or "").strip():
            raise LLMRequestError("llm_empty_response", "The selected model returned no text. Try a different model.", 422)

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


def build_ai_provider(provider: str, model: str, api_key: str, base_url: str | None = None) -> BaseAIProvider:
    if provider in PROVIDERS:
        return PROVIDERS[provider](model, api_key)
    return HTTPProvider(model, api_key, provider=provider, base_url=base_url)


def provider_error(exc: Exception) -> LLMRequestError:
    """Map SDK failures without returning provider bodies, URLs or headers."""
    if isinstance(exc, LLMRequestError):
        return exc
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
    code = getattr(exc, "code", None)
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body = exc.response.json()
            code = body.get("error", {}).get("code") if isinstance(body, dict) and isinstance(body.get("error"), dict) else None
        except ValueError:
            code = None
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

class HTTPProvider(BaseAIProvider):
    """Chat Completions and Anthropic Messages, with no automatic redirects."""
    def __init__(self, model, api_key, *, provider, base_url=None, **kwargs):
        super().__init__(model, api_key, **kwargs)
        from app.ai.endpoints import validate_endpoint
        self.provider = provider
        self.base_url = validate_endpoint(base_url or "") if provider == "custom" else {
            "openrouter": "https://openrouter.ai/api/v1",
            "groq": "https://api.groq.com/openai/v1",
            "anthropic": "https://api.anthropic.com/v1",
        }[provider]

    def request(self, method, path, **kwargs):
        from app.ai.endpoints import PublicEndpointTransport
        headers = ({"x-api-key": self.api_key, "anthropic-version": "2026-10-21"}
                   if self.provider == "anthropic" else {"Authorization": f"Bearer {self.api_key}"})
        with httpx.Client(transport=PublicEndpointTransport() if self.provider == "custom" else None,
                          trust_env=False, follow_redirects=False, timeout=kwargs.pop("timeout", self.settings.openai_timeout)) as client:
            response = client.request(method, self.base_url + path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    def discover_models(self):
        models = []
        params = {}
        for _ in range(20):
            data = self.request("GET", "/models", params=params, timeout=12)
            for row in data.get("data", []):
                name = row.get("id", "")
                if self.provider == "openrouter" and "text" not in row.get("architecture", {}).get("output_modalities", ["text"]):
                    continue
                if any(word in name.lower() for word in ("whisper", "embedding", "tts", "guard", "transcri")):
                    continue
                models.append(name)
            if not data.get("has_more") or not data.get("last_id"):
                break
            params = {"after_id": data["last_id"]}
        return models

    def _generate(self, system_prompt, user_prompt, limit, timeout=None):
        if self.provider == "anthropic":
            data = self.request("POST", "/messages", timeout=timeout or self.settings.openai_timeout, json={"model": self.model, "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}], "max_tokens": limit})
            return "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text")
        data = self.request("POST", "/chat/completions", timeout=timeout or self.settings.openai_timeout, json={"model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            ("max_completion_tokens" if self.provider == "groq" else "max_tokens"): limit})
        return data["choices"][0]["message"]["content"] or ""

    def test_connection(self):
        if not self._generate("Reply briefly.", "Reply OK.", 256, timeout=12).strip():
            raise LLMRequestError("llm_empty_response", "The model returned no text. Choose a text generation model.", 422)

    def generate_content(self, *, system_prompt, user_prompt):
        return self._generate(system_prompt, user_prompt, self.settings.max_ai_tokens)
