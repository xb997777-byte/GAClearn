from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from django.utils import timezone

from apps.users.models import UserSetting

from .chroma_runtime import chroma_available, embed_texts, get_chroma_client
from .knowledge_base import CHROMA_COLLECTION
from .personalized_knowledge import build_personalized_knowledge_chunks, split_personalized_payload


def get_personalized_collection_name(user_id: int) -> str:
    return f"{CHROMA_COLLECTION}_user_{int(user_id)}"


def get_personalized_collection(user_id: int):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=get_personalized_collection_name(user_id),
        metadata={"hnsw:space": "cosine"},
    )


def delete_personalized_collection(user_id: int):
    client = get_chroma_client()
    try:
        client.delete_collection(get_personalized_collection_name(user_id))
    except Exception:
        pass


@dataclass
class PersonalizedRagSyncResult:
    mode: str
    user_id: int
    total_chunks: int
    upserted_count: int
    indexed_count_after_sync: int
    source_type_breakdown: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode,
            "user_id": self.user_id,
            "total_chunks": self.total_chunks,
            "upserted_count": self.upserted_count,
            "indexed_count_after_sync": self.indexed_count_after_sync,
            "source_type_breakdown": self.source_type_breakdown,
        }


def sync_personalized_rag_for_user(user) -> Dict[str, object]:
    if not chroma_available():
        raise RuntimeError("Chroma runtime is not installed")

    setting, _ = UserSetting.objects.get_or_create(user=user)
    if not setting.personalized_rag_enabled:
        raise ValueError("personalized rag is disabled for this user")

    setting.personalized_rag_status = "building"
    setting.personalized_rag_last_error = ""
    setting.save(update_fields=["personalized_rag_status", "personalized_rag_last_error", "updated_at"])

    try:
        bundle = build_personalized_knowledge_chunks(user)
        ids, documents, metadatas = split_personalized_payload(bundle.chunks)
        collection = get_personalized_collection(user.id)
        collection.delete(where={"user_id": int(user.id)})
        embeddings = embed_texts(documents) if documents else []
        if documents:
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        indexed_count = int(collection.count())
        setting.personalized_rag_status = "ready"
        setting.personalized_rag_chunk_count = indexed_count
        setting.personalized_rag_updated_at = timezone.now()
        setting.personalized_rag_last_error = ""
        setting.save(
            update_fields=[
                "personalized_rag_status",
                "personalized_rag_chunk_count",
                "personalized_rag_updated_at",
                "personalized_rag_last_error",
                "updated_at",
            ]
        )
        return PersonalizedRagSyncResult(
            mode="manual_rebuild",
            user_id=user.id,
            total_chunks=len(bundle.chunks),
            upserted_count=len(ids),
            indexed_count_after_sync=indexed_count,
            source_type_breakdown=bundle.summary.get("source_type_breakdown", {}),
        ).to_dict()
    except Exception as exc:
        setting.personalized_rag_status = "failed"
        setting.personalized_rag_last_error = str(exc)
        setting.save(update_fields=["personalized_rag_status", "personalized_rag_last_error", "updated_at"])
        raise


def search_personalized_knowledge(user, query: str, limit: int = 6) -> List[Dict[str, object]]:
    if not chroma_available():
        return []

    setting = UserSetting.objects.filter(user=user).first()
    if not setting or not setting.personalized_rag_enabled or setting.personalized_rag_status != "ready":
        return []

    collection = get_personalized_collection(user.id)
    if int(collection.count()) <= 0:
        return []

    query_embeddings = embed_texts([query])
    result = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(max(int(limit or 6), 1), 12),
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
                "source_type": metadata.get("source_type", "personalized_chunk"),
                "source_id": metadata.get("source_id", user.id),
                "title": metadata.get("title", ""),
                "content": document,
                "content_preview": str(document or "")[:280],
                "score": round(max(0.0, 1.0 - distance), 4),
                "metadata": {
                    **metadata,
                    "source_scope": "personalized",
                },
            }
        )
    return rows
