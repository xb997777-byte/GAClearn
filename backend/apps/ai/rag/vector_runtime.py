from collections import Counter
import math
import re

from apps.books.models import Word
from apps.grammar.models import GrammarPoint, GrammarSentence


VECTOR_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z-']+|[\u4e00-\u9fff]+")


def tokenize_for_vector(text):
    tokens = []
    for token in VECTOR_TOKEN_PATTERN.findall((text or "").lower()):
        if not token:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            tokens.extend(list(token))
            tokens.extend(token[index : index + 2] for index in range(max(len(token) - 1, 0)))
        elif token not in {"the", "and", "for", "with", "from", "that", "this", "your"} and len(token) > 2:
            tokens.append(token)
    return tokens


def vectorize_text(text):
    return Counter(tokenize_for_vector(text))


def cosine_score(left, right):
    if not left or not right:
        return 0
    overlap = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0
    return dot / (left_norm * right_norm)


def build_local_vector_documents():
    docs = []
    for item in Word.objects.select_related("book").order_by("book_id", "order_in_book", "id")[:500]:
        content = " ".join(
            [
                item.word,
                item.meaning_cn,
                item.part_of_speech,
                item.synonyms,
                item.example_sentence,
                item.example_translation,
            ]
        )
        docs.append(
            {
                "source_type": "word",
                "source_id": item.id,
                "title": item.word,
                "content": content,
                "metadata": {"book_id": item.book_id, "book_name": item.book.name},
            }
        )
    for item in GrammarPoint.objects.filter(status="active").order_by("sort_order", "id")[:240]:
        content = " ".join([item.title, item.category, item.description, item.learning_tip, item.practice_prompt])
        docs.append(
            {
                "source_type": "grammar_point",
                "source_id": item.id,
                "title": item.title,
                "content": content,
                "metadata": {"category": item.category, "difficulty": item.difficulty},
            }
        )
    sentences = (
        GrammarSentence.objects.select_related("point")
        .filter(status="active", point__status="active")
        .order_by("point__sort_order", "order_in_point", "id")[:500]
    )
    for item in sentences:
        content = " ".join([item.sentence, item.translation_cn, item.summary, item.analysis, item.point.title, item.scene_tag])
        docs.append(
            {
                "source_type": "grammar_sentence",
                "source_id": item.id,
                "title": item.sentence[:80],
                "content": content,
                "metadata": {"point_id": item.point_id, "point_title": item.point.title, "difficulty": item.difficulty},
            }
        )
    return docs


class LocalHashVectorStore:
    runtime_info = {
        "type": "local_hash_vector",
        "version": "vector_rag_v2",
        "backend": "in_process_counter_cosine",
        "embedding_model": "token-hash-counter",
        "external_vector_db": False,
        "langchain_ready": True,
    }

    def search(self, query, limit=8):
        query_vector = vectorize_text(query)
        scored = []
        for doc in build_local_vector_documents():
            score = cosine_score(query_vector, vectorize_text(f"{doc['title']} {doc['content']}"))
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            scored = [(0, doc) for doc in build_local_vector_documents()[:limit]]
        return [
            {
                **doc,
                "score": round(score, 4),
                "content_preview": doc["content"][:240],
            }
            for score, doc in scored[: min(max(int(limit or 8), 1), 12)]
        ]


def get_vector_runtime():
    return dict(LocalHashVectorStore.runtime_info)
