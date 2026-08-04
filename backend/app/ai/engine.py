"""Thin AI engine wrapper that sends prompts to the configured provider and parses the response."""

from __future__ import annotations

from typing import Any
import logging
import json

from app.ai.context_builder import PatientContext
from app.ai.prompt_builder import PromptBuilder
from app.ai.response_parser import ResponseParser
from app.core.config import get_settings


class AIEngine:
    """Coordinate prompt construction and AI provider interaction without database access."""

    def __init__(self, *, provider: Any | None = None, client: Any | None = None) -> None:
        self.settings = get_settings()
        # Defer importing the provider factory so heavy SDK imports don't run at module import time.
        if provider is not None:
            self.provider = provider
        else:
            from app.ai.providers import build_ai_provider

            self.provider = build_ai_provider(settings=self.settings, client=client)
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()

    def analyze(self, context: PatientContext) -> dict[str, Any]:
        """Build prompts, call the configured AI provider, and return structured JSON."""
        system_prompt = self.prompt_builder.build_system_prompt(context)
        user_prompt = self.prompt_builder.build_user_prompt(context)
        content = self.provider.generate_content(system_prompt=system_prompt, user_prompt=user_prompt)
        logger = logging.getLogger(__name__)
        # Log raw provider output for debugging schema mismatches
        try:
            if isinstance(content, (dict, list)):
                logger.debug("Raw provider content (dict/list): %s", json.dumps(content, default=str, ensure_ascii=False))
            else:
                logger.debug("Raw provider content (str): %s", content)
        except Exception:
            logger.exception("Failed to log raw provider content")

        if not content:
            raise ValueError("AI provider returned no content.")
        return self.response_parser.parse(content)
