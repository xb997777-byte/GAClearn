import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import requests


DEFAULT_TIMEOUT = int(os.getenv("AI_EMBEDDING_TIMEOUT_SECONDS", "40") or 40)
DEFAULT_BATCH_SIZE = int(os.getenv("AI_EMBEDDING_API_BATCH_SIZE", "10") or 10)
DEFAULT_MAX_BATCH_SIZE = int(os.getenv("AI_EMBEDDING_API_MAX_BATCH_SIZE", "10") or 10)
DEFAULT_RETRIES = max(int(os.getenv("AI_EMBEDDING_API_RETRIES", "3") or 3), 1)
DEFAULT_CONCURRENCY = max(int(os.getenv("AI_EMBEDDING_API_CONCURRENCY", "4") or 4), 1)


def _clean_env(name: str, default: str = "") -> str:
    value = str(os.getenv(name, default) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def embedding_provider_ready() -> bool:
    return bool(_clean_env("AI_EMBEDDING_API_KEY")) and bool(_clean_env("AI_EMBEDDING_MODEL")) and bool(
        _clean_env("AI_EMBEDDING_BASE_URL")
    )


def _request_embedding_batch(api_key: str, model: str, base_url: str, batch: List[str]) -> List[List[float]]:
    last_error = None
    response = None
    for attempt in range(1, DEFAULT_RETRIES + 1):
        try:
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
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= DEFAULT_RETRIES:
                detail = response.text[:500] if response is not None else ""
                raise RuntimeError(f"Embedding API request failed: {exc}. detail={detail}") from exc
            time.sleep(min(1.5 * attempt, 4.0))

    if response is None:
        raise RuntimeError(f"Embedding API request failed: {last_error}")

    payload = response.json()
    rows = payload.get("data") or []
    if not rows:
        raise RuntimeError("Embedding response is empty")

    ordered = sorted(rows, key=lambda item: item.get("index", 0))
    vectors = []
    for item in ordered:
        embedding = item.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("Embedding vector is missing")
        vectors.append([float(value) for value in embedding])
    return vectors


def embed_texts_openai_compatible(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    api_key = _clean_env("AI_EMBEDDING_API_KEY")
    model = _clean_env("AI_EMBEDDING_MODEL")
    base_url = _clean_env("AI_EMBEDDING_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    if not api_key or not model or not base_url:
        raise RuntimeError("Embedding provider is not configured")

    vectors = []
    batch_size = max(min(DEFAULT_BATCH_SIZE, DEFAULT_MAX_BATCH_SIZE), 1)
    batches = [texts[start : start + batch_size] for start in range(0, len(texts), batch_size)]
    if not batches:
        return vectors
    if len(batches) == 1:
        return _request_embedding_batch(api_key, model, base_url, batches[0])

    concurrency = min(DEFAULT_CONCURRENCY, len(batches))
    indexed_results = {}
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(_request_embedding_batch, api_key, model, base_url, batch): index
            for index, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            batch_index = futures[future]
            indexed_results[batch_index] = future.result()

    for index in range(len(batches)):
        vectors.extend(indexed_results.get(index, []))
    return vectors
