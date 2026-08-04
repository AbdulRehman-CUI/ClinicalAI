"""Construct system and user prompts for AI analysis."""

from __future__ import annotations

from typing import Any

from app.ai.context_builder import PatientContext
from app.core.config import get_settings


class PromptBuilder:
    """Create prompts from a structured patient context."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def build_system_prompt(self, context: PatientContext) -> str:
        return (
            "You are a clinical decision support assistant. "
            "You must not diagnose definitively, and you must clearly state uncertainty. "
            "IMPORTANT: Return ONLY a single JSON OBJECT and nothing else. The object MUST contain the following keys: \n"
            "- summary\n- medication_warnings\n- possible_diagnoses\n- recommended_tests\n- recommended_specialist\n- critical_alerts\n"
            "Do NOT include any explanatory text, markdown, or code fences. Do NOT wrap the object in lists or additional envelopes. "
            "If you cannot provide valid JSON, return an empty JSON object {}."
        )

    def build_user_prompt(self, context: PatientContext) -> str:
        sections: list[str] = ["Patient context:"]
        sections.append(self._format_section("patient", context.patient))
        sections.append(self._format_section("medical_history", context.medical_history))
        sections.append(self._format_section("allergies", context.allergies))
        sections.append(self._format_section("medications", context.medications))
        sections.append(self._format_section("symptoms", context.symptoms))
        if context.reports:
            sections.append("reports:\n" + self._truncate(context.reports))
        return "\n\n".join(sections)

    def _truncate(self, value: str) -> str:
        if len(value) <= self.settings.max_context_length:
            return value
        return value[: self.settings.max_context_length - 3] + "..."

    def _format_section(self, name: str, value: Any) -> str:
        if isinstance(value, dict):
            items = [f"{key}: {item}" for key, item in value.items() if item not in (None, "")]
            return f"{name}:\n" + "\n".join(items) if items else f"{name}: []"
        if isinstance(value, list):
            if not value:
                return f"{name}: []"
            rendered = []
            for item in value:
                if isinstance(item, dict):
                    details = [f"{key}: {entry}" for key, entry in item.items() if entry not in (None, "")]
                    rendered.append("{ " + ", ".join(details) + " }")
                else:
                    rendered.append(str(item))
            return f"{name}:\n" + "\n".join(rendered)
        return f"{name}: {value}"
