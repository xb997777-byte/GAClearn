from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .chroma_runtime import chroma_available, embed_texts, get_chroma_collection
from .knowledge_base import build_all_knowledge_chunks, split_chroma_payload


@dataclass
class RagSyncResult:
    mode: str
    total_chunks: int
    upserted_count: int
    skipped_count: int
    deleted_count: int
    indexed_count_after_sync: int

    def to_dict(self) -> Dict[str, int | str]:
        return {
            "mode": self.mode,
            "total_chunks": self.total_chunks,
            "upserted_count": self.upserted_count,
            "skipped_count": self.skipped_count,
            "deleted_count": self.deleted_count,
            "indexed_count_after_sync": self.indexed_count_after_sync,
        }


def _batch_rows(rows: List[Dict[str, object]], batch_size: int) -> Iterable[List[Dict[str, object]]]:
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def sync_rag_index(limit: int | None = None, batch_size: int = 64, delete_missing: bool = False) -> RagSyncResult:
    if not chroma_available():
        raise RuntimeError("Chroma runtime is not installed")

    chunks = build_all_knowledge_chunks(limit=limit)
    ids, documents, metadatas = split_chroma_payload(chunks)
    rows = [
        {
            "id": ids[index],
            "document": documents[index],
            "metadata": metadatas[index],
        }
        for index in range(len(ids))
    ]

    collection = get_chroma_collection()
    existing = collection.get(include=["metadatas"])
    existing_ids = existing.get("ids") or []
    existing_metadatas = existing.get("metadatas") or []
    existing_hash_map = {}
    for index, chunk_id in enumerate(existing_ids):
        metadata = existing_metadatas[index] if index < len(existing_metadatas) else {}
        existing_hash_map[chunk_id] = (metadata or {}).get("content_hash", "")

    rows_to_upsert: List[Dict[str, object]] = []
    skipped_count = 0
    expected_ids = set()
    for row in rows:
        chunk_id = str(row["id"])
        expected_ids.add(chunk_id)
        content_hash = (row.get("metadata") or {}).get("content_hash", "")
        if existing_hash_map.get(chunk_id) == content_hash:
            skipped_count += 1
            continue
        rows_to_upsert.append(row)

    deleted_count = 0
    if delete_missing:
        missing_ids = [chunk_id for chunk_id in existing_ids if chunk_id not in expected_ids]
        if missing_ids:
            collection.delete(ids=missing_ids)
            deleted_count = len(missing_ids)

    upserted_count = 0
    for batch in _batch_rows(rows_to_upsert, max(int(batch_size or 64), 1)):
        batch_ids = [str(item["id"]) for item in batch]
        batch_documents = [str(item["document"]) for item in batch]
        batch_metadatas = [dict(item["metadata"] or {}) for item in batch]
        embeddings = embed_texts(batch_documents)
        collection.upsert(
            ids=batch_ids,
            documents=batch_documents,
            metadatas=batch_metadatas,
            embeddings=embeddings,
        )
        upserted_count += len(batch_ids)

    indexed_count_after_sync = int(collection.count())
    return RagSyncResult(
        mode="incremental_sync",
        total_chunks=len(rows),
        upserted_count=upserted_count,
        skipped_count=skipped_count,
        deleted_count=deleted_count,
        indexed_count_after_sync=indexed_count_after_sync,
    )
