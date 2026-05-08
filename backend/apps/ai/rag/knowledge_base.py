import hashlib
import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from apps.books.models import Word, WordExample
from apps.grammar.models import GrammarPoint, GrammarSentence

from .vector_runtime import tokenize_for_vector


CHROMA_DIR = os.getenv("AI_CHROMA_DIR", os.path.join("media", "ai_chroma"))
CHROMA_COLLECTION = os.getenv("AI_CHROMA_COLLECTION", "english_learning_knowledge")
CHUNK_VERSION = "rag_chunk_v1"
KNOWLEDGE_SOURCE_DETAILS = [
    {
        "key": "words",
        "label": "单词主表",
        "table": "words",
        "description": "单词、词性、中文释义、近义词和主例句等核心词条内容。",
    },
    {
        "key": "word_examples",
        "label": "单词例句表",
        "table": "word_examples",
        "description": "补充单词在真实句子里的使用方式与中文翻译。",
    },
    {
        "key": "grammar_points",
        "label": "语法点表",
        "table": "grammar_points",
        "description": "语法点标题、分类、说明、学习提示与练习提示。",
    },
    {
        "key": "grammar_sentences",
        "label": "语法句子表",
        "table": "grammar_sentences",
        "description": "和语法点绑定的示例句、翻译、摘要、解析与场景信息。",
    },
]


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source_type: str
    source_id: int
    title: str
    content: str
    metadata: Dict[str, object]


def _clean_text(*parts: object) -> str:
    values = []
    for part in parts:
        text = str(part or "").strip()
        if text:
            values.append(text)
    return "\n".join(values)


def _make_chunk_id(source_type: str, source_id: int, suffix: str) -> str:
    raw = f"{CHUNK_VERSION}:{source_type}:{source_id}:{suffix}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _token_summary(text: str, limit: int = 18) -> str:
    tokens = tokenize_for_vector(text)
    if not tokens:
        return ""
    seen = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return ", ".join(seen[:limit])


def _content_hash(source_type: str, source_id: int, title: str, content: str, metadata: Dict[str, object]) -> str:
    payload = {
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "content": content,
        "metadata": metadata,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_word_chunks(limit: int | None = None) -> List[KnowledgeChunk]:
    queryset = (
        Word.objects.select_related("book")
        .filter(book__status="active")
        .order_by("book_id", "order_in_book", "id")
    )
    if limit:
        queryset = queryset[:limit]

    chunks: List[KnowledgeChunk] = []
    for item in queryset:
        head_content = _clean_text(
            f"单词：{item.word}",
            f"词性：{item.part_of_speech}",
            f"中文释义：{item.meaning_cn}",
            f"近义词：{item.synonyms}",
            f"主例句：{item.example_sentence}",
            f"例句翻译：{item.example_translation}",
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("word", item.id, "core"),
                source_type="word",
                source_id=item.id,
                title=item.word,
                content=head_content,
                metadata={
                    "book_id": item.book_id,
                    "book_name": item.book.name,
                    "chunk_kind": "word_core",
                    "difficulty": item.difficulty,
                    "part_of_speech": item.part_of_speech,
                    "keyword_hints": _token_summary(head_content),
                    "chunk_version": CHUNK_VERSION,
                },
            )
        )

    examples = (
        WordExample.objects.select_related("word", "word__book")
        .filter(word__book__status="active")
        .order_by("word_id", "sort_order", "id")
    )
    if limit:
        examples = examples[: limit * 2]
    for item in examples:
        content = _clean_text(
            f"单词：{item.word.word}",
            f"例句：{item.example_sentence}",
            f"翻译：{item.example_translation}",
            f"词义：{item.word.meaning_cn}",
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("word_example", item.id, "example"),
                source_type="word_example",
                source_id=item.id,
                title=f"{item.word.word} 例句",
                content=content,
                metadata={
                    "word_id": item.word_id,
                    "word": item.word.word,
                    "book_id": item.word.book_id,
                    "book_name": item.word.book.name,
                    "chunk_kind": "word_example",
                    "sort_order": item.sort_order,
                    "keyword_hints": _token_summary(content),
                    "chunk_version": CHUNK_VERSION,
                },
            )
        )
    return chunks


def build_grammar_chunks(limit: int | None = None) -> List[KnowledgeChunk]:
    points = GrammarPoint.objects.filter(status="active").order_by("sort_order", "id")
    if limit:
        points = points[:limit]

    chunks: List[KnowledgeChunk] = []
    for item in points:
        content = _clean_text(
            f"语法点：{item.title}",
            f"分类：{item.category}",
            f"说明：{item.description}",
            f"学习提示：{item.learning_tip}",
            f"练习提示：{item.practice_prompt}",
            f"练习解析：{item.practice_explanation}",
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("grammar_point", item.id, "core"),
                source_type="grammar_point",
                source_id=item.id,
                title=item.title,
                content=content,
                metadata={
                    "category": item.category,
                    "difficulty": item.difficulty,
                    "chunk_kind": "grammar_point",
                    "keyword_hints": _token_summary(content),
                    "chunk_version": CHUNK_VERSION,
                },
            )
        )

    sentences = (
        GrammarSentence.objects.select_related("point")
        .filter(status="active", point__status="active")
        .order_by("point__sort_order", "order_in_point", "id")
    )
    if limit:
        sentences = sentences[: limit * 2]
    for item in sentences:
        content = _clean_text(
            f"语法点：{item.point.title}",
            f"句子：{item.sentence}",
            f"翻译：{item.translation_cn}",
            f"摘要：{item.summary}",
            f"解析：{item.analysis}",
            f"场景：{item.scene_tag}",
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("grammar_sentence", item.id, "sentence"),
                source_type="grammar_sentence",
                source_id=item.id,
                title=item.sentence[:80],
                content=content,
                metadata={
                    "point_id": item.point_id,
                    "point_title": item.point.title,
                    "difficulty": item.difficulty,
                    "scene_tag": item.scene_tag,
                    "chunk_kind": "grammar_sentence",
                    "keyword_hints": _token_summary(content),
                    "chunk_version": CHUNK_VERSION,
                },
            )
        )
    return chunks


def build_all_knowledge_chunks(limit: int | None = None) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    chunks.extend(build_word_chunks(limit=limit))
    chunks.extend(build_grammar_chunks(limit=limit))
    return chunks


def chunk_stats(chunks: Iterable[KnowledgeChunk]) -> Dict[str, int]:
    stats: Dict[str, int] = {}
    for item in chunks:
        stats[item.source_type] = stats.get(item.source_type, 0) + 1
    return stats


def get_knowledge_source_catalog() -> List[Dict[str, object]]:
    counts = {
        "words": Word.objects.filter(book__status="active").count(),
        "word_examples": WordExample.objects.filter(word__book__status="active").count(),
        "grammar_points": GrammarPoint.objects.filter(status="active").count(),
        "grammar_sentences": GrammarSentence.objects.filter(status="active", point__status="active").count(),
    }
    catalog: List[Dict[str, object]] = []
    for item in KNOWLEDGE_SOURCE_DETAILS:
        catalog.append(
            {
                **item,
                "record_count": counts.get(item["key"], 0),
            }
        )
    return catalog


def split_chroma_payload(chunks: Iterable[KnowledgeChunk]) -> Tuple[List[str], List[str], List[Dict[str, object]]]:
    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, object]] = []
    for item in chunks:
        ids.append(item.chunk_id)
        documents.append(item.content)
        payload_metadata = {
            "source_type": item.source_type,
            "source_id": item.source_id,
            "title": item.title,
            **item.metadata,
        }
        payload_metadata["content_hash"] = _content_hash(
            item.source_type,
            item.source_id,
            item.title,
            item.content,
            payload_metadata,
        )
        metadatas.append(
            payload_metadata
        )
    return ids, documents, metadatas
