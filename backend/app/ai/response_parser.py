"""Validate and normalize AI responses into the documented JSON structure."""

from __future__ import annotations

import json
import re
from typing import Any


class ResponseParser:
    """Ensure AI responses are valid JSON and conform to the expected structure."""

    required_keys = {
        "possible_diagnoses",
        "medication_warnings",
        "critical_alerts",
        "recommended_tests",
        "recommended_specialist",
        "summary",
    }

    def parse(self, payload: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError as exc:
                repaired = self._repair_json(payload)
                if repaired is None:
                    raise ValueError("AI response was not valid JSON.") from exc
                parsed = repaired
        elif isinstance(payload, dict):
            parsed = payload
        else:
            raise ValueError("AI response must be a JSON string or object.")

        if not isinstance(parsed, dict):
            raise ValueError("AI response must be a JSON object.")

        missing = self.required_keys.difference(parsed.keys())
        if missing:
            raise ValueError(f"AI response is missing required keys: {sorted(missing)}")

        normalized = {
            "possible_diagnoses": self._ensure_list(parsed.get("possible_diagnoses")),
            "medication_warnings": self._ensure_list(parsed.get("medication_warnings")),
            "critical_alerts": self._ensure_list(parsed.get("critical_alerts")),
            "recommended_tests": self._ensure_list(parsed.get("recommended_tests")),
            "recommended_specialist": self._ensure_string(parsed.get("recommended_specialist")),
            "summary": self._ensure_string(parsed.get("summary")),
        }
        return normalized

    def _repair_json(self, payload: str) -> dict[str, Any] | None:
        cleaned = payload.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match is None:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _ensure_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _ensure_string(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)
