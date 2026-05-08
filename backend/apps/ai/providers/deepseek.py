import json
import os

import requests


DEFAULT_TIMEOUT = int(os.getenv("AI_TIMEOUT_SECONDS", "40") or 40)


def is_provider_ready():
    return bool(os.getenv("AI_API_KEY", "").strip()) and bool(os.getenv("AI_MODEL", "").strip())


def _extract_json_block(content):
    content = (content or "").strip()
    if content.startswith("```"):
        parts = content.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate
    return content


def chat_completion(messages, temperature=0.25):
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    if not api_key or not model:
        raise RuntimeError("AI service is not configured")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": temperature,
            "messages": messages,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("AI response is empty")
    content = ((choices[0] or {}).get("message") or {}).get("content", "")
    if not content:
        raise RuntimeError("AI message content is empty")
    return content.strip()


def chat_json(messages, temperature=0.2):
    content = chat_completion(messages, temperature=temperature)
    return json.loads(_extract_json_block(content))
