import json
import re

from anthropic import Anthropic

import config


def _get_client() -> Anthropic:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
    return Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _extract_text(response) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def reason_with_json(system: str, user: str, max_tokens: int = 1024) -> dict:
    client = _get_client()
    last_error: Exception | None = None
    last_text = ""

    base_system = f"{system.rstrip()}\n\nRespond ONLY with valid JSON. No markdown, no preamble."

    for attempt in range(2):
        system_prompt = base_system
        if attempt == 1:
            system_prompt += (
                "\n\nYour previous response was not valid JSON. "
                "Return exactly one valid JSON object and nothing else."
            )

        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            system=system_prompt,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user}],
        )
        last_text = _strip_json_fences(_extract_text(response))

        try:
            parsed = json.loads(last_text)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        if not isinstance(parsed, dict):
            last_error = ValueError("Claude did not return a JSON object.")
            continue

        return parsed

    raise ValueError(f"Claude returned invalid JSON: {last_text}") from last_error


def compose_text(system: str, user: str, max_tokens: int = 800) -> str:
    client = _get_client()
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        system=system,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": user}],
    )
    return _extract_text(response).strip()
