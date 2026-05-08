import os
from functools import lru_cache
from typing import Dict, List

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
        try:
            if DEFAULT_EMBEDDING_PROVIDER != "openai_compatible":
                raise RuntimeError(f"Unsupported embedding provider: {DEFAULT_EMBEDDING_PROVIDER}")
            return embed_texts_openai_compatible(texts)
        except Exception:
            if sentence_transformers_available():
                try:
                    model = get_embedding_model()
                    vectors = model.encode(texts, normalize_embeddings=True)
                    return [vector.tolist() for vector in vectors]
                except Exception:
                    return _hash_embed_texts(texts)
            return _hash_embed_texts(texts)
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
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def reset_chroma_collection():
    client = get_chroma_client()
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def search_knowledge_base(query: str, limit: int = 8) -> List[Dict[str, object]]:
    if not chroma_available():
        raise RuntimeError("Chroma runtime is not installed")

    collection = get_chroma_collection()
    query_embeddings = embed_texts([query])
    result = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(max(int(limit or 8), 1), 12),
        include=["documents", "metadatas", "distances"],
    )
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    rows: List[Dict[str, object]] = []
    for index, document in enumerate(documents):
        metadata = dict((metadatas[index] or {})) if index < len(metadatas) else {}
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
    return rows


def get_chroma_collection_stats() -> Dict[str, object]:
    if not chroma_available():
        return {
            "available": False,
            "indexed": False,
            "chunk_count": 0,
            "chunk_version": CHUNK_VERSION,
        }
    try:
        collection = get_chroma_collection()
        count = int(collection.count())
        return {
            "available": True,
            "indexed": count > 0,
            "chunk_count": count,
            "chunk_version": CHUNK_VERSION,
        }
    except Exception as exc:
        return {
            "available": True,
            "indexed": False,
            "chunk_count": 0,
            "chunk_version": CHUNK_VERSION,
            "error": str(exc),
        }


def get_chroma_runtime() -> Dict[str, object]:
    collection_stats = get_chroma_collection_stats()
    embedding_backend = _select_embedding_backend()
    return {
        "type": "chroma_vector_db",
        "version": "vector_rag_v3",
        "backend": "chromadb_persistent_local",
        "embedding_model": (
            DEFAULT_EMBEDDING_MODEL
            if embedding_backend == "online"
            else LOCAL_EMBEDDING_MODEL if embedding_backend == "sentence_transformers" else "token-hash-counter"
        ),
        "embedding_backend": embedding_backend,
        "embedding_provider": DEFAULT_EMBEDDING_PROVIDER if embedding_backend == "online" else "",
        "external_vector_db": True,
        "knowledge_sources": [item["key"] for item in KNOWLEDGE_SOURCE_DETAILS],
        "knowledge_source_catalog": get_knowledge_source_catalog(),
        "storage_path": CHROMA_DIR,
        "collection_name": CHROMA_COLLECTION,
        "available": chroma_available(),
        "indexed": collection_stats.get("indexed", False),
        "chunk_count": collection_stats.get("chunk_count", 0),
        "chunk_version": collection_stats.get("chunk_version", CHUNK_VERSION),
        "rebuild_command": "python manage.py rebuild_rag_index",
        "retrieval_mode": "project_knowledge_base",
        "fallback_runtime": "local_hash_vector",
        "notes": [
            "标准 RAG 的知识来源优先来自项目自己的教学数据表，而不是外部网页。",
            "当 Chroma 依赖不可用时，会自动回退到本地轻量向量检索。",
            "当语义 embedding 模型首次下载失败时，会临时降级为离线 hash embedding，但仍保留 Chroma 入库与召回链路。",
        ],
        **({"last_error": collection_stats["error"]} if collection_stats.get("error") else {}),
    }
