"""LLM client for parsing availability text and generating slot explanations."""

import json
import os
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app.schema import StructuredAvailability


class LLMClient:
    """OpenAI-compatible chat completion client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def _chat(self, messages: list[dict[str, str]]) -> str:
        """Call chat completion and return content."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from model output (handles markdown code blocks)."""
        text = text.strip()
        # Try to find ```json ... ``` block first
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
        # Try to find raw {...}
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return match.group(0)
        return text

    def parse_availability_text(self, text: str) -> StructuredAvailability:
        """
        Convert free-text availability into StructuredAvailability.
        Uses strict JSON extraction with Pydantic validation and retry on failure.
        """
        schema_desc = """
The JSON must have exactly these fields (all required except noted):
- provider_id: string
- timezone: string (IANA e.g. America/New_York)
- slot_length_minutes: int (default 30)
- buffer_minutes: int (default 10)
- business_hours: {"start": "HH:MM", "end": "HH:MM"}
- date_range: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
- existing_appointments: [{"start": "ISO8601", "end": "ISO8601"}]
- preferred_days: [0-6] (0=Monday, 6=Sunday)
- preferred_times: [{"start": "HH:MM", "end": "HH:MM"}]
"""

        prompt = f"""Convert the following availability description into a strict JSON object.
{schema_desc}
Return ONLY valid JSON, no markdown, no explanation.

Availability text:
{text}
"""

        messages = [{"role": "user", "content": prompt}]
        raw = self._chat(messages)
        json_str = self._extract_json(raw)

        try:
            data = json.loads(json_str)
            return StructuredAvailability.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            # Retry with repair prompt
            repair_prompt = f"""The previous JSON was invalid. Error: {e}
Original text: {text}

Fix the JSON to match the schema. Return ONLY valid JSON.
{schema_desc}
"""
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": repair_prompt})
            raw2 = self._chat(messages)
            json_str2 = self._extract_json(raw2)
            data = json.loads(json_str2)
            return StructuredAvailability.model_validate(data)

    def explain_slots(
        self,
        slots: list[dict[str, Any]],
        availability: StructuredAvailability,
    ) -> list[str]:
        """
        Generate 1-2 sentence explanation for each suggested slot.
        """
        if not slots:
            return []

        slots_desc = "\n".join(
            f"- {s['start_iso']} to {s['end_iso']} (provider: {s['provider_id']})"
            for s in slots
        )

        prompt = f"""Given this availability context:
- Provider: {availability.provider_id}
- Timezone: {availability.timezone}
- Business hours: {availability.business_hours.start}-{availability.business_hours.end}
- Preferred days: {availability.preferred_days}
- Preferred times: {availability.preferred_times}

These {len(slots)} slots were suggested:
{slots_desc}

For each slot (in the same order), write exactly one short sentence (1-2 sentences max) explaining why it was chosen. Return a JSON array of strings, one per slot. Example: ["First slot...", "Second slot...", ...]
Return ONLY the JSON array, no other text."""

        raw = self._chat([{"role": "user", "content": prompt}])
        json_str = self._extract_json(raw)

        try:
            explanations = json.loads(json_str)
            if isinstance(explanations, list) and len(explanations) >= len(slots):
                return [str(e) for e in explanations[: len(slots)]]
            # Fallback: one generic explanation per slot
            return [
                f"Slot fits within business hours and preferred times for provider {availability.provider_id}."
                for _ in slots
            ]
        except (json.JSONDecodeError, TypeError):
            return [
                f"Slot fits within business hours and preferred times for provider {availability.provider_id}."
                for _ in slots
            ]
