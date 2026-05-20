import os
import hashlib
from functools import lru_cache
from typing import Dict, List, Tuple

from ..providers.embeddings import embed_texts_openai_compatible, embedding_provider_ready
from .vector_runtime import vectorize_text

from .knowledge_base import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    CHUNK_VERSION,
    KNOWLEDGE_SOURCE_DETAILS,
    get_knowledge_source_catalog,
)


DEFAULT_EMBEDDING_MODEL = os.getenv("AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_EMBEDDING_BACKEND = os.getenv("AI_EMBEDDING_BACKEND", "auto").strip().lower() or "auto"
DEFAULT_EMBEDDING_PROVIDER = os.getenv("AI_EMBEDDING_PROVIDER", "openai_compatible").strip().lower() or "openai_compatible"
LOCAL_EMBEDDING_MODEL = os.getenv("AI_LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HASH_EMBEDDING_DIM = int(os.getenv("AI_HASH_EMBEDDING_DIM", "512") or 512)
EMBEDDING_RUNTIME_CACHE_TTL_SECONDS = max(int(os.getenv("AI_RAG_RUNTIME_CACHE_TTL_SECONDS", "8") or 8), 1)


def _clean_env(name: str, default: str = "") -> str:
    value = str(os.getenv(name, default) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def chroma_available() -> bool:
    try:
        import chromadb  # noqa: F401
    except ImportError:
        return False
    return True


def sentence_transformers_available() -> bool:
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError:
        return False
    return True


def standard_chroma_runtime_ready() -> bool:
    return chroma_available() and sentence_transformers_available()


def _remote_embedding_dimension_hint(model_name: str) -> int:
    normalized = str(model_name or "").strip().lower()
    known_dimensions = {
        "text-embedding-v4": 1024,
        "text-embedding-3-large": 3072,
        "text-embedding-3-small": 1536,
        "text-embedding-ada-002": 1536,
    }
    if normalized in known_dimensions:
        return known_dimensions[normalized]
    explicit = int(_clean_env("AI_EMBEDDING_DIMENSION", "0") or 0)
    return explicit if explicit > 0 else 0


def _ensure_parent_dir() -> None:
    os.makedirs(CHROMA_DIR, exist_ok=True)


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(LOCAL_EMBEDDING_MODEL)


def _select_embedding_backend() -> str:
    if DEFAULT_EMBEDDING_BACKEND in {"hash", "local_hash"}:
        return "hash"
    if DEFAULT_EMBEDDING_BACKEND in {"online", "remote", "api"}:
        return "online"
    if DEFAULT_EMBEDDING_BACKEND in {"sentence_transformers", "st"}:
        return "sentence_transformers"
    if embedding_provider_ready():
        return "online"
    if sentence_transformers_available():
        return "sentence_transformers"
    return "hash"


def get_effective_embedding_dimension() -> int:
    backend = _select_embedding_backend()
    if backend == "hash":
        return HASH_EMBEDDING_DIM
    if backend == "online":
        hinted = _remote_embedding_dimension_hint(DEFAULT_EMBEDDING_MODEL)
        if hinted > 0:
            return hinted
    try:
        vectors = embed_texts(["dimension probe"])
    except Exception:
        return HASH_EMBEDDING_DIM if backend == "hash" else 0
    if not vectors:
        return 0
    return len(vectors[0] or [])


def get_effective_embedding_name() -> str:
    backend = _select_embedding_backend()
    if backend == "online":
        return DEFAULT_EMBEDDING_MODEL
    if backend == "sentence_transformers":
        return LOCAL_EMBEDDING_MODEL
    return "token-hash-counter"


def get_collection_fingerprint() -> str:
    backend = _select_embedding_backend()
    provider = DEFAULT_EMBEDDING_PROVIDER if backend == "online" else backend
    model = get_effective_embedding_name()
    dimension = get_effective_embedding_dimension()
    raw = f"{CHUNK_VERSION}:{provider}:{model}:{dimension}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def get_chroma_collection_name() -> str:
    return f"{CHROMA_COLLECTION}_{get_collection_fingerprint()}"


def list_chroma_collection_names() -> List[str]:
    if not chroma_available():
        return []
    client = get_chroma_client()
    names = []
    for item in client.list_collections():
        name = getattr(item, "name", "") or ""
        if name.startswith(CHROMA_COLLECTION):
            names.append(name)
    return sorted(names)


def list_stale_collection_names() -> List[str]:
    active_name = get_chroma_collection_name()
    return [name for name in list_chroma_collection_names() if name != active_name]


def _hash_embedding(text: str, dim: int = HASH_EMBEDDING_DIM) -> List[float]:
    vector = [0.0] * dim
    counter = vectorize_text(text)
    if not counter:
        return vector
    for token, weight in counter.items():
        index = hash(token) % dim
        vector[index] += float(weight)

    norm = sum(value * value for value in vector) ** 0.5
    if norm <= 0:
        return vector
    return [value / norm for value in vector]


def _hash_embed_texts(texts: List[str]) -> List[List[float]]:
    return [_hash_embedding(text) for text in texts]


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    backend = _select_embedding_backend()
    if backend == "online":
        if DEFAULT_EMBEDDING_PROVIDER != "openai_compatible":
            raise RuntimeError(f"Unsupported embedding provider: {DEFAULT_EMBEDDING_PROVIDER}")
        # Do not silently fall back to a different embedding dimension when the
        # active collection fingerprint has already been computed for online
        # embeddings. Mixed 1024/384 vectors would corrupt the collection.
        return embed_texts_openai_compatible(texts)
    if backend == "hash":
        return _hash_embed_texts(texts)
    try:
        model = get_embedding_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]
    except Exception:
        return _hash_embed_texts(texts)


def get_chroma_client():
    import chromadb

    _ensure_parent_dir()
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_chroma_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=get_chroma_collection_name(),
        metadata={
            "hnsw:space": "cosine",
            "chunk_version": CHUNK_VERSION,
            "collection_fingerprint": get_collection_fingerprint(),
            "embedding_dimension": get_effective_embedding_dimension(),
        },
    )


def reset_chroma_collection():
    client = get_chroma_client()
    try:
        client.delete_collection(get_chroma_collection_name())
    except Exception:
        pass
    return client.get_or_create_collection(
        name=get_chroma_collection_name(),
        metadata={
            "hnsw:space": "cosine",
            "chunk_version": CHUNK_VERSION,
            "collection_fingerprint": get_collection_fingerprint(),
            "embedding_dimension": get_effective_embedding_dimension(),
        },
    )


def _matches_audience(metadata: Dict[str, object], allowed_audiences: List[str] | None) -> bool:
    if not allowed_audiences:
        return True
    audience = str((metadata or {}).get("audience", "") or "").strip()
    if not audience:
        return True
    return audience in allowed_audiences


def search_knowledge_base(query: str, limit: int = 8, allowed_audiences: List[str] | None = None) -> List[Dict[str, object]]:
    if not chroma_available():
        raise RuntimeError("Chroma runtime is not installed")

    collection = get_chroma_collection()
    query_embeddings = embed_texts([query])
    result = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(max(int(limit or 8), 1), 12) * 3,
        include=["documents", "metadatas", "distances"],
    )
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    rows: List[Dict[str, object]] = []
    for index, document in enumerate(documents):
        metadata = dict((metadatas[index] or {})) if index < len(metadatas) else {}
        if not _matches_audience(metadata, allowed_audiences):
            continue
        distance = float(distances[index]) if index < len(distances) and distances[index] is not None else 1.0
        rows.append(
            {
                "source_type": metadata.get("source_type", "knowledge_chunk"),
                "source_id": metadata.get("source_id", 0),
                "title": metadata.get("title", ""),
                "content": document,
                "content_preview": str(document or "")[:280],
                "score": round(max(0.0, 1.0 - distance), 4),
                "metadata": metadata,
            }
        )
    return rows[: min(max(int(limit or 8), 1), 12)]


def get_chroma_collection_stats() -> Dict[str, object]:
    if not chroma_available():
        return {
            "available": False,
            "indexed": False,
            "chunk_count": 0,
            "chunk_version": CHUNK_VERSION,
            "runtime_ready": False,
            "dependency_state": "missing_chromadb",
            "error": "缺少 chromadb 依赖，标准向量运行时不可用。",
        }
    try:
        collection = get_chroma_collection()
        count = int(collection.count())
        metadata = getattr(collection, "metadata", None) or {}
        return {
            "available": True,
            "indexed": count > 0,
            "chunk_count": count,
            "chunk_version": CHUNK_VERSION,
            "collection_name": get_chroma_collection_name(),
            "collection_fingerprint": get_collection_fingerprint(),
            "embedding_dimension": int(metadata.get("embedding_dimension") or get_effective_embedding_dimension() or 0),
            "stale_collections": list_stale_collection_names(),
            "runtime_ready": standard_chroma_runtime_ready(),
            "dependency_state": "ready" if standard_chroma_runtime_ready() else "missing_sentence_transformers",
        }
    except Exception as exc:
        return {
            "available": False,
            "indexed": False,
            "chunk_count": 0,
            "chunk_version": CHUNK_VERSION,
            "collection_name": get_chroma_collection_name(),
            "collection_fingerprint": get_collection_fingerprint(),
            "embedding_dimension": get_effective_embedding_dimension(),
            "stale_collections": list_stale_collection_names(),
            "error": str(exc),
            "runtime_ready": standard_chroma_runtime_ready(),
            "dependency_state": "error",
        }


def get_chroma_runtime() -> Dict[str, object]:
    collection_stats = get_chroma_collection_stats()
    embedding_backend = _select_embedding_backend()
    embedding_model_name = get_effective_embedding_name()
    embedding_dimension = int(collection_stats.get("embedding_dimension") or get_effective_embedding_dimension() or 0)
    catalog = get_knowledge_source_catalog()
    expected_chunk_count = 0
    source_breakdown = []
    for item in catalog:
        item_chunk_count = int(item.get("chunk_count") or item.get("record_count") or 0)
        expected_chunk_count += item_chunk_count
        source_breakdown.append(
            {
                "key": item.get("key", ""),
                "label": item.get("label", ""),
                "record_count": int(item.get("record_count") or 0),
                "chunk_count": item_chunk_count,
            }
        )
    runtime_chunk_count = int(collection_stats.get("chunk_count") or 0)
    dependency_state = str(collection_stats.get("dependency_state") or "").strip()
    runtime_ready = bool(collection_stats.get("runtime_ready"))
    collection_health = "healthy"
    runtime_degraded_reason = ""
    if dependency_state == "missing_chromadb":
        collection_health = "missing_dependency"
        runtime_degraded_reason = "缺少 chromadb 依赖，标准向量运行时不可用。"
    elif dependency_state == "missing_sentence_transformers":
        collection_health = "missing_dependency"
        runtime_degraded_reason = "缺少 sentence-transformers 依赖，标准本地向量运行时不可用。"
    elif collection_stats.get("error"):
        collection_health = "error"
        runtime_degraded_reason = f"Chroma collection 打开失败：{collection_stats.get('error')}"
    elif not collection_stats.get("available"):
        collection_health = "unavailable"
        runtime_degraded_reason = "标准向量运行时当前不可用。"
    elif expected_chunk_count and runtime_chunk_count < expected_chunk_count:
        collection_health = "partial"
        runtime_degraded_reason = "标准向量索引未达到预期块数，当前处于部分可用状态。"
    available = bool(collection_stats.get("available")) and runtime_ready and not collection_stats.get("error")
    indexed = bool(collection_stats.get("indexed")) and runtime_ready and runtime_chunk_count > 0
    return {
        "type": "chroma_vector_db",
        "version": "vector_rag_v4",
        "backend": "chromadb_persistent_local",
        "embedding_model": embedding_model_name,
        "embedding_backend": embedding_backend,
        "embedding_provider": DEFAULT_EMBEDDING_PROVIDER if embedding_backend == "online" else "",
        "embedding_dimension": embedding_dimension,
        "external_vector_db": True,
        "knowledge_sources": [item["key"] for item in KNOWLEDGE_SOURCE_DETAILS],
        "knowledge_source_catalog": catalog,
        "source_breakdown": source_breakdown,
        "expected_chunk_count": expected_chunk_count,
        "storage_path": CHROMA_DIR,
        "collection_name": collection_stats.get("collection_name", get_chroma_collection_name()),
        "collection_fingerprint": collection_stats.get("collection_fingerprint", get_collection_fingerprint()),
        "available": available,
        "indexed": indexed,
        "chunk_count": runtime_chunk_count,
        "chunk_version": collection_stats.get("chunk_version", CHUNK_VERSION),
        "collection_health": collection_health,
        "stale_collections": collection_stats.get("stale_collections", []),
        "runtime_ready": runtime_ready,
        "runtime_degraded": collection_health != "healthy",
        "runtime_degraded_reason": runtime_degraded_reason,
        "dependency_state": dependency_state or ("ready" if runtime_ready else "unknown"),
        "rebuild_command": "python manage.py rebuild_rag_index",
        "retrieval_mode": "project_knowledge_base",
        "fallback_runtime": "local_hash_vector",
        "notes": [
            "标准 RAG 的知识来源优先来自项目自己的教学数据表，而不是外部网页。",
            "当 Chroma 依赖不可用时，会自动回退到本地轻量向量检索。",
            "当语义 embedding 模型首次下载失败时，会临时降级为离线 hash embedding，但仍保留 Chroma 入库与召回链路。",
            "collection 会按 chunk_version + provider + model + embedding_dimension 生成 fingerprint，避免旧索引维度污染。",
        ],
        **({"last_error": collection_stats["error"]} if collection_stats.get("error") else {}),
    }
