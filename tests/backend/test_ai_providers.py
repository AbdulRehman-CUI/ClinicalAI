from __future__ import annotations

from app.ai.engine import AIEngine
from app.ai.providers import GeminiProvider, OpenAIProvider, build_ai_provider


def test_gemini_provider_uses_current_sdk_config_names(monkeypatch) -> None:
    captured_config: dict[str, object] = {}

    class FakeConfig:
        def __init__(self, **kwargs) -> None:
            captured_config.update(kwargs)

    class FakeResponse:
        text = "ok"

    class FakeModels:
        def generate_content(self, **kwargs) -> FakeResponse:
            return FakeResponse()

    fake_client = type("FakeClient", (), {"models": FakeModels()})()

    monkeypatch.setattr("app.ai.providers.types.GenerateContentConfig", FakeConfig)

    provider = GeminiProvider("gemini-3.6-flash", "test-gemini-key", client=fake_client)

    result = provider.generate_content(system_prompt="system", user_prompt="user")

    assert result == "ok"
    assert captured_config["systemInstruction"] == "system"
    assert captured_config["maxOutputTokens"] == provider.settings.max_ai_tokens


def test_ai_engines_keep_request_provider_settings_separate() -> None:
    openai = AIEngine(provider=build_ai_provider("openai", "gpt-4.1-mini", "test-openai-key"))
    gemini = AIEngine(provider=build_ai_provider("gemini", "gemini-3.6-flash", "test-gemini-key"))
    assert isinstance(openai.provider, OpenAIProvider)
    assert isinstance(gemini.provider, GeminiProvider)
    assert (openai.provider.model, openai.provider.api_key) == ("gpt-4.1-mini", "test-openai-key")
    assert (gemini.provider.model, gemini.provider.api_key) == ("gemini-3.6-flash", "test-gemini-key")
