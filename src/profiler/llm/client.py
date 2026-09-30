"""Talk to Ollama over its REST API and turn page text into a validated Profile."""

import json
import os
import re

import requests

from .schema import Profile

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
MAX_CHARS = 30_000
TIMEOUT_SECONDS = 300

SYSTEM_PROMPT = """You extract structured information about ONE person from the text of their portfolio website.

Rules:
- Use ONLY information stated in the text. Never guess or invent anything.
- If something is not mentioned, use null (or an empty list).
- Keep descriptions short and faithful to the original wording.
- Reply with a single JSON object that matches this JSON schema. No commentary, no markdown.

Schema:
{schema}"""


class LLMError(RuntimeError):
    """Ollama was unreachable, returned an error, or gave an unusable answer."""


def list_models() -> list[str]:
    """Names of the models Ollama knows about (empty list if it is not running)."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]
    except (requests.RequestException, ValueError):
        return []


def parse_profile(raw: str) -> Profile:
    """Validate the model's reply. Tolerates markdown fences and stray text around the JSON."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in the model reply")
    return Profile.model_validate_json(raw[start : end + 1])


def _chat(messages: list[dict], model: str) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": Profile.model_json_schema(),  # ask Ollama to enforce the schema
        "options": {"temperature": 0},
    }
    try:
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise LLMError(f"Could not reach Ollama at {OLLAMA_URL}. Is it running? ({exc})") from exc
    if response.status_code != 200:
        raise LLMError(f"Ollama returned {response.status_code}: {response.text[:300]}")
    return response.json()["message"]["content"]


def extract_profile(text: str, model: str = DEFAULT_MODEL) -> Profile:
    """Ask the model for a Profile. If the first reply is invalid, ask once more."""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n[text truncated]"

    schema = json.dumps(Profile.model_json_schema())
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema)},
        {"role": "user", "content": f"Portfolio website text:\n\n{text}"},
    ]

    raw = _chat(messages, model)
    try:
        return parse_profile(raw)
    except ValueError as first_error:
        messages += [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": f"That reply was not valid ({str(first_error)[:500]}). "
                "Reply again with only the corrected JSON object.",
            },
        ]

    raw = _chat(messages, model)
    try:
        return parse_profile(raw)
    except ValueError as exc:
        raise LLMError(f"The model did not return valid JSON: {str(exc)[:300]}") from exc
