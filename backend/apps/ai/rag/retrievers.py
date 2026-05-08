import re

from django.db.models import Q

from apps.grammar.models import GrammarPoint, GrammarSentence
from apps.grammar.services import DIFFICULTY_LABELS

from ..compat import Document, LANGCHAIN_CORE_AVAILABLE


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z\-']+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "why",
    "will",
    "with",
    "you",
    "your",
}


def extract_query_keywords(*texts, extra_tags=None):
    keywords = []
    for text in texts:
        for token in TOKEN_PATTERN.findall((text or "").lower()):
            if token in STOPWORDS or len(token) <= 2 or token in keywords:
                continue
            keywords.append(token)
    for tag in extra_tags or []:
        token = str(tag or "").strip()
        if token and token not in keywords:
            keywords.append(token)
    return keywords[:12]


def _score_text_hits(text, keywords):
    text = (text or "").lower()
    score = 0
    matched = []
    for keyword in keywords:
        if keyword.lower() in text:
            score += 1
            matched.append(keyword)
    return score, matched


def _serialize_point(point, reason):
    return {
        "id": point.id,
        "code": point.code,
        "title": point.title,
        "category": point.category,
        "difficulty": point.difficulty,
        "difficulty_label": DIFFICULTY_LABELS.get(point.difficulty, "基础"),
        "description": point.description,
        "learning_tip": point.learning_tip,
        "reason": reason,
    }


def _serialize_sentence(sentence, reason):
    return {
        "id": sentence.id,
        "point_id": sentence.point_id,
        "point_title": sentence.point.title,
        "sentence": sentence.sentence,
        "translation_cn": sentence.translation_cn,
        "summary": sentence.summary,
        "difficulty": sentence.difficulty,
        "difficulty_label": DIFFICULTY_LABELS.get(sentence.difficulty, "基础"),
        "reason": reason,
    }


def retrieve_related_points(detail, question="", limit=3):
    keywords = extract_query_keywords(
        detail.get("sentence", ""),
        detail.get("summary", ""),
        detail.get("analysis", ""),
        question,
        extra_tags=detail.get("grammar_tags") or [],
    )
    queryset = GrammarPoint.objects.filter(status="active")
    if keywords:
        q = Q()
        for keyword in keywords[:8]:
            q |= Q(title__icontains=keyword)
            q |= Q(description__icontains=keyword)
            q |= Q(learning_tip__icontains=keyword)
            q |= Q(category__icontains=keyword)
            q |= Q(code__icontains=keyword)
        queryset = queryset.filter(q)

    scored = []
    for point in queryset.order_by("sort_order", "id")[:40]:
        title_score, title_hits = _score_text_hits(point.title, keywords)
        desc_score, desc_hits = _score_text_hits(f"{point.description} {point.learning_tip} {point.category}", keywords)
        tag_bonus = 0
        for tag in detail.get("grammar_tags") or []:
            if tag and tag in f"{point.title} {point.description} {point.category}":
                tag_bonus += 2
        total_score = title_score * 3 + desc_score * 2 + tag_bonus
        if total_score <= 0 and keywords:
            continue
        hits = title_hits + desc_hits
        reason = "命中了相关语法标签"
        if hits:
            reason = f"命中了关键词：{' / '.join(list(dict.fromkeys(hits))[:3])}"
        scored.append((total_score, point, reason))

    scored.sort(key=lambda item: (-item[0], item[1].difficulty, item[1].sort_order, item[1].id))
    if scored:
        return [_serialize_point(point, reason) for _, point, reason in scored[:limit]]

    fallback_points = GrammarPoint.objects.filter(status="active").order_by("difficulty", "sort_order", "id")[:limit]
    return [_serialize_point(point, "作为当前句型的邻近语法点，可用于顺延学习。") for point in fallback_points]


def retrieve_similar_sentences(detail, question="", limit=4):
    keywords = extract_query_keywords(
        detail.get("sentence", ""),
        detail.get("summary", ""),
        detail.get("analysis", ""),
        question,
        extra_tags=detail.get("grammar_tags") or [],
    )
    queryset = GrammarSentence.objects.select_related("point").filter(status="active", point__status="active")
    if keywords:
        q = Q()
        for keyword in keywords[:8]:
            q |= Q(sentence__icontains=keyword)
            q |= Q(summary__icontains=keyword)
            q |= Q(analysis__icontains=keyword)
            q |= Q(translation_cn__icontains=keyword)
            q |= Q(point__title__icontains=keyword)
        queryset = queryset.filter(q)

    current_sentence = (detail.get("sentence") or "").strip().lower()
    current_difficulty = int(detail.get("difficulty") or 1)
    current_tags = set(detail.get("grammar_tags") or [])
    scored = []

    for sentence in queryset.order_by("point__sort_order", "order_in_point", "id")[:80]:
        if sentence.sentence.strip().lower() == current_sentence:
            continue
        sentence_score, sentence_hits = _score_text_hits(
            f"{sentence.sentence} {sentence.summary} {sentence.analysis} {sentence.point.title}",
            keywords,
        )
        tag_bonus = 0
        for tag in sentence.grammar_tags or []:
            if tag in current_tags:
                tag_bonus += 2
        if sentence.point.title in current_tags:
            tag_bonus += 2
        difficulty_bonus = max(0, 3 - abs(sentence.difficulty - current_difficulty))
        total_score = sentence_score * 2 + tag_bonus + difficulty_bonus
        if total_score <= 0 and keywords:
            continue
        reason = "难度与语法结构接近"
        if sentence_hits:
            reason = f"与当前句子共享关键词：{' / '.join(list(dict.fromkeys(sentence_hits))[:3])}"
        elif tag_bonus:
            reason = "与当前句子共享语法标签"
        scored.append((total_score, sentence, reason))

    scored.sort(key=lambda item: (-item[0], abs(item[1].difficulty - current_difficulty), item[1].id))
    return [_serialize_sentence(sentence, reason) for _, sentence, reason in scored[:limit]]


def build_grammar_retrieval_bundle(detail, question=""):
    related_points = retrieve_related_points(detail, question=question, limit=3)
    similar_sentences = retrieve_similar_sentences(detail, question=question, limit=4)
    keywords = extract_query_keywords(
        detail.get("sentence", ""),
        detail.get("summary", ""),
        detail.get("analysis", ""),
        question,
        extra_tags=detail.get("grammar_tags") or [],
    )
    return {
        "keywords": keywords,
        "related_points": related_points,
        "similar_sentences": similar_sentences,
    }


def as_langchain_documents(retrieval_bundle):
    if not LANGCHAIN_CORE_AVAILABLE:
        return []

    docs = []
    for point in retrieval_bundle.get("related_points") or []:
        docs.append(
            Document(
                page_content=f"{point['title']}：{point['description']} 学习提示：{point['learning_tip']}",
                metadata={"source_type": "grammar_point", "source_id": point["id"]},
            )
        )
    for sentence in retrieval_bundle.get("similar_sentences") or []:
        docs.append(
            Document(
                page_content=f"{sentence['sentence']} | {sentence['translation_cn']} | {sentence['summary']}",
                metadata={"source_type": "grammar_sentence", "source_id": sentence["id"]},
            )
        )
    return docs
