from __future__ import annotations

from app.ai.engine import AIEngine
from app.ai.providers import GeminiProvider, OpenAIProvider
from app.core.config import Settings


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

    provider = GeminiProvider(
        settings=Settings(
            ai_provider="gemini",
            openai_api_key=None,
            openai_model="gpt-4o-mini",
            gemini_api_key="test-gemini-key",
            gemini_model="gemini-2.5-flash",
        ),
        client=fake_client,
    )

    result = provider.generate_content(system_prompt="system", user_prompt="user")

    assert result == "ok"
    assert captured_config["systemInstruction"] == "system"
    assert captured_config["maxOutputTokens"] == provider.settings.max_ai_tokens


def test_ai_engine_uses_openai_provider_for_openai_setting(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.ai.engine.get_settings",
        lambda: Settings(
            ai_provider="openai",
            openai_api_key="test-openai-key",
            openai_model="gpt-4o-mini",
            gemini_api_key=None,
            gemini_model="gemini-2.5-flash",
        ),
    )

    engine = AIEngine()

    assert isinstance(engine.provider, OpenAIProvider)


def test_ai_engine_uses_gemini_provider_for_gemini_setting(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.ai.engine.get_settings",
        lambda: Settings(
            ai_provider="gemini",
            openai_api_key=None,
            openai_model="gpt-4o-mini",
            gemini_api_key="test-gemini-key",
            gemini_model="gemini-2.5-flash",
        ),
    )

    engine = AIEngine()

    assert isinstance(engine.provider, GeminiProvider)
