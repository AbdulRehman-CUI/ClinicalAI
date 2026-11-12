"""Thin AI engine wrapper that sends prompts to the configured provider and parses the response."""

from __future__ import annotations

from typing import Any

from app.ai.context_builder import PatientContext
from app.ai.prompt_builder import PromptBuilder
from app.ai.response_parser import ResponseParser


class AIEngine:
    """Coordinate prompt construction and AI provider interaction without database access."""

    def __init__(self, *, provider: Any) -> None:
        self.provider = provider
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()

    def analyze(self, context: PatientContext) -> dict[str, Any]:
        """Build prompts, call the configured AI provider, and return structured JSON."""
        system_prompt = self.prompt_builder.build_system_prompt(context)
        user_prompt = self.prompt_builder.build_user_prompt(context)
        content = self.provider.generate_content(system_prompt=system_prompt, user_prompt=user_prompt)
        if not content:
            raise ValueError("AI provider returned no content.")
        return self.response_parser.parse(content)
