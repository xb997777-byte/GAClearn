import os
from typing import List

import requests


DEFAULT_TIMEOUT = int(os.getenv("AI_EMBEDDING_TIMEOUT_SECONDS", "40") or 40)
DEFAULT_BATCH_SIZE = int(os.getenv("AI_EMBEDDING_API_BATCH_SIZE", "8") or 8)


def _clean_env(name: str, default: str = "") -> str:
    value = str(os.getenv(name, default) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def embedding_provider_ready() -> bool:
    return bool(_clean_env("AI_EMBEDDING_API_KEY")) and bool(_clean_env("AI_EMBEDDING_MODEL")) and bool(
        _clean_env("AI_EMBEDDING_BASE_URL")
    )


def embed_texts_openai_compatible(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    api_key = _clean_env("AI_EMBEDDING_API_KEY")
    model = _clean_env("AI_EMBEDDING_MODEL")
    base_url = _clean_env("AI_EMBEDDING_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    if not api_key or not model or not base_url:
        raise RuntimeError("Embedding provider is not configured")

    vectors = []
    batch_size = max(DEFAULT_BATCH_SIZE, 1)
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = requests.post(
            f"{base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": batch,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text[:500]
            raise RuntimeError(f"Embedding API request failed: {exc}. detail={detail}") from exc
        payload = response.json()
        rows = payload.get("data") or []
        if not rows:
            raise RuntimeError("Embedding response is empty")

        ordered = sorted(rows, key=lambda item: item.get("index", 0))
        for item in ordered:
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("Embedding vector is missing")
            vectors.append([float(value) for value in embedding])
    return vectors
