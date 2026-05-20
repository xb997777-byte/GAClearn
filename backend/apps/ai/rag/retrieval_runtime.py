from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List

from ..rag.chroma_runtime import chroma_available, get_chroma_runtime, search_knowledge_base
from ..rag.personalized_runtime import search_personalized_knowledge
from ..rag.vector_runtime import LocalHashVectorStore, get_vector_runtime


@dataclass
class RetrievalRuntimeResult:
    query: str
    mode: str
    documents: List[Dict[str, Any]]
    structured_context: Dict[str, Any]
    retrieval_strategy: Dict[str, Any]
    diagnostics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode,
            "documents": self.documents,
            "structured_context": self.structured_context,
            "retrieval_strategy": self.retrieval_strategy,
            "diagnostics": self.diagnostics,
        }


def merge_documents(primary_docs: List[Dict[str, Any]], secondary_docs: List[Dict[str, Any]], *, secondary_origin: str, score_boost: float = 0.0, limit: int = 8) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    ordered_keys: List[str] = []

    def touch(doc: Dict[str, Any], implicit_origin: str, extra_boost: float = 0.0) -> None:
        payload = dict(doc or {})
        key = f"{payload.get('source_type', '')}:{payload.get('source_id', '')}:{payload.get('title', '')}"
        payload["score"] = round(float(payload.get("score", 0) or 0) + float(extra_boost or 0), 4)
        payload["retrieval_sources"] = list(dict.fromkeys((payload.get("retrieval_sources") or []) + [implicit_origin]))
        if key not in merged:
            merged[key] = payload
            ordered_keys.append(key)
            return
        current = merged[key]
        current["score"] = round(max(float(current.get("score", 0) or 0), float(payload.get("score", 0) or 0)), 4)
        current["retrieval_sources"] = list(
            dict.fromkeys((current.get("retrieval_sources") or []) + (payload.get("retrieval_sources") or []))
        )
        if len(str(payload.get("content_preview", ""))) > len(str(current.get("content_preview", ""))):
            current["content_preview"] = payload.get("content_preview", "")
        if len(str(payload.get("content", ""))) > len(str(current.get("content", ""))):
            current["content"] = payload.get("content", "")
        metadata = dict(current.get("metadata") or {})
        metadata.update(payload.get("metadata") or {})
        current["metadata"] = metadata

    for item in primary_docs or []:
        touch(item, (item.get("retrieval_sources") or ["vector"])[0])
    for item in secondary_docs or []:
        touch(item, secondary_origin, score_boost)

    rows = [merged[key] for key in ordered_keys]
    rows.sort(
        key=lambda item: (
            -("personalized" in (item.get("retrieval_sources") or [])),
            -len(item.get("retrieval_sources", [])),
            -(float(item.get("score", 0) or 0)),
            str(item.get("title", "")),
        )
    )
    return rows[: min(max(int(limit or 8), 1), 12)]


def rerank_documents(query: str, docs: List[Dict[str, Any]], keywords: List[str], limit: int = 8) -> List[Dict[str, Any]]:
    query_lower = str(query or "").lower()
    exact_tokens = []
    for token in re.findall(r"[A-Za-z][A-Za-z-']+", query_lower):
        normalized = token.strip().lower()
        if normalized and normalized not in exact_tokens:
            exact_tokens.append(normalized)
    reranked: List[Dict[str, Any]] = []
    for index, item in enumerate(docs or []):
        doc = dict(item or {})
        base_score = float(doc.get("score", 0) or 0)
        metadata = dict(doc.get("metadata") or {})
        title_lower = str(doc.get("title", "")).lower()
        haystack = " ".join(
            [
                str(doc.get("title", "")),
                str(doc.get("content_preview", "")),
                str(doc.get("content", "")),
            ]
        ).lower()
        keyword_hits = sum(1 for keyword in keywords[:10] if keyword and keyword.lower() in haystack)
        full_query_bonus = 0.08 if query_lower and query_lower in haystack else 0.0
        dual_source_bonus = 0.06 if len(doc.get("retrieval_sources") or []) >= 2 else 0.0
        personalized_bonus = 0.04 if "personalized" in (doc.get("retrieval_sources") or []) else 0.0
        title_bonus = 0.03 if any(keyword.lower() in title_lower for keyword in keywords[:6]) else 0.0
        exact_title_hits = sum(1 for token in exact_tokens[:6] if token == title_lower)
        exact_title_bonus = min(exact_title_hits * 0.28, 0.56)
        multi_token_bonus = 0.16 if len(exact_tokens) >= 2 and sum(1 for token in exact_tokens[:6] if token in haystack) >= 2 else 0.0
        exact_match_bonus = 0.18 if str(metadata.get("match_quality") or "") == "exact" else 0.0
        structured_bonus = 0.2 if "structured" in (doc.get("retrieval_sources") or []) else 0.0
        audience = str((metadata.get("audience")) or "").strip()
        audience_bonus = 0.06 if audience == "learning" else (0.03 if audience in {"product", "migration"} else 0.0)
        rerank_score = round(
            base_score
            + keyword_hits * 0.025
            + full_query_bonus
            + dual_source_bonus
            + personalized_bonus
            + title_bonus
            + exact_title_bonus
            + multi_token_bonus
            + exact_match_bonus
            + structured_bonus
            + audience_bonus,
            4,
        )
        doc["rerank_score"] = rerank_score
        doc["rank_debug"] = {
            "base_score": round(base_score, 4),
            "keyword_hits": keyword_hits,
            "full_query_bonus": full_query_bonus,
            "dual_source_bonus": dual_source_bonus,
            "personalized_bonus": personalized_bonus,
            "title_bonus": title_bonus,
            "exact_title_bonus": exact_title_bonus,
            "multi_token_bonus": multi_token_bonus,
            "exact_match_bonus": exact_match_bonus,
            "structured_bonus": structured_bonus,
            "audience_bonus": audience_bonus,
            "pre_rerank_index": index,
        }
        reranked.append(doc)

    reranked.sort(
        key=lambda item: (
            -(float(item.get("rerank_score", 0) or 0)),
            -len(item.get("retrieval_sources", [])),
            str(item.get("title", "")),
        )
    )
    return reranked[: min(max(int(limit or 8), 1), 12)]


def build_retrieval_strategy(
    *,
    mode: str,
    using_chroma: bool,
    structured_hits: int,
    vector_hits: int,
    personalized_hits: int,
    normalized_query: str = "",
    query_expansions: List[str] | None = None,
) -> Dict[str, Any]:
    base = dict(get_chroma_runtime() if using_chroma else get_vector_runtime())
    base.update(
        {
            "type": "unified_retrieval_runtime",
            "version": "retrieval_layer_v1",
            "retrieval_mode": mode,
            "structured_hits": structured_hits,
            "vector_hits": vector_hits,
            "personalized_hits": personalized_hits,
            "personalized_enabled": personalized_hits > 0,
            "rerank_enabled": True,
            "multi_route_enabled": True,
            "normalized_query": normalized_query,
            "query_expansions": query_expansions or [],
            "degraded": not using_chroma,
            "backend": base.get("backend") or ("chromadb_persistent_local" if using_chroma else "in_process_counter_cosine"),
            "active_retrieval_backend": base.get("backend") or ("chromadb_persistent_local" if using_chroma else "in_process_counter_cosine"),
        }
    )
    if not using_chroma:
        base["degraded_reason"] = "标准 Chroma 向量运行时不可用，已回退到结构化优先 + 本地轻量向量兜底。"
    return base


def load_vector_documents(
    query: str,
    limit: int,
    user=None,
    allowed_audiences: List[str] | None = None,
) -> tuple[List[Dict[str, Any]], bool, List[Dict[str, Any]], str]:
    personalized_docs: List[Dict[str, Any]] = []
    if user is not None:
        try:
            personalized_docs = search_personalized_knowledge(user, query, limit=limit)
        except Exception:
            personalized_docs = []

    project_docs: List[Dict[str, Any]] = []
    using_chroma = False
    backend_name = ""
    if chroma_available():
        try:
            project_docs = search_knowledge_base(query, limit=limit, allowed_audiences=allowed_audiences)
            using_chroma = bool(project_docs)
            if using_chroma:
                backend_name = "chromadb_persistent_local"
        except Exception:
            project_docs = []
    if not project_docs:
        project_docs = LocalHashVectorStore().search(query, limit=limit)
        backend_name = "in_process_counter_cosine"

    merged = merge_documents(project_docs, personalized_docs, secondary_origin="personalized", score_boost=0.05, limit=limit)
    return merged, using_chroma, personalized_docs, backend_name or ("chromadb_persistent_local" if using_chroma else "in_process_counter_cosine")
