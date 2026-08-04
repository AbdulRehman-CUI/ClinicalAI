"""AI foundation components for ClinicalAI."""

from app.ai.context_builder import PatientContextBuilder
from app.ai.engine import AIEngine
from app.ai.prompt_builder import PromptBuilder
from app.ai.providers import BaseAIProvider, GeminiProvider, OpenAIProvider, build_ai_provider
from app.ai.report_processor import ReportProcessor
from app.ai.response_parser import ResponseParser

__all__ = [
    "AIEngine",
    "BaseAIProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "PatientContextBuilder",
    "PromptBuilder",
    "ReportProcessor",
    "ResponseParser",
    "build_ai_provider",
]
