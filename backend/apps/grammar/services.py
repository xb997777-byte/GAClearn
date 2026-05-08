from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from .models import GrammarAnnotation, GrammarLearningRecord, GrammarPoint, GrammarSentence


DIFFICULTY_LABELS = {
    1: "基础",
    2: "进阶",
    3: "考试",
}

ROLE_LABELS = {
    "subject": "主语",
    "predicate": "谓语",
    "object": "宾语",
    "complement": "表语/补语",
    "adverbial": "状语",
    "modifier": "定语/修饰语",
    "clause": "从句",
    "connector": "连接词",
    "infinitive": "不定式",
    "gerund": "动名词",
    "comparison": "比较结构",
    "agent": "动作发出者",
}

COLOR_PALETTE = {
    "plain": {"label": "普通文本", "bg": "#ffffff", "color": "#344054"},
    "subject": {"label": "主语", "bg": "#e4f7ea", "color": "#166534"},
    "predicate": {"label": "谓语", "bg": "#fff1dc", "color": "#b45309"},
    "object": {"label": "宾语", "bg": "#e5f0ff", "color": "#1d4ed8"},
    "complement": {"label": "表语/补语", "bg": "#fce7f3", "color": "#be185d"},
    "adverbial": {"label": "状语", "bg": "#ede9fe", "color": "#6d28d9"},
    "modifier": {"label": "定语/修饰语", "bg": "#e6fffb", "color": "#0f766e"},
    "clause": {"label": "从句", "bg": "#fee2e2", "color": "#b91c1c"},
    "connector": {"label": "连接词", "bg": "#f3f4f6", "color": "#475467"},
    "infinitive": {"label": "不定式", "bg": "#ffe7d6", "color": "#c2410c"},
    "gerund": {"label": "动名词", "bg": "#dcfce7", "color": "#15803d"},
    "comparison": {"label": "比较结构", "bg": "#ede9fe", "color": "#7c3aed"},
    "agent": {"label": "动作发出者", "bg": "#dbeafe", "color": "#1d4ed8"},
}

CORE_ROLES = {"subject", "predicate", "object", "complement"}


def paginate_queryset(queryset, page=1, page_size=20):
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    start = (page - 1) * page_size
    end = start + page_size
    return queryset[start:end], queryset.count(), page, page_size


def build_legend():
    order = [
        "subject",
        "predicate",
        "object",
        "complement",
        "adverbial",
        "modifier",
        "clause",
        "connector",
        "infinitive",
        "gerund",
        "comparison",
        "agent",
    ]
    result = []
    for token in order:
        item = COLOR_PALETTE[token]
        result.append(
            {
                "token": token,
                "label": item["label"],
                "background": item["bg"],
                "color": item["color"],
            }
        )
    return result


def _difficulty_label(value):
    return DIFFICULTY_LABELS.get(value, "基础")


def _palette_for(token):
    return COLOR_PALETTE.get(token or "plain", COLOR_PALETTE["plain"])


def _annotation_label(annotation):
    return annotation.grammar_label or ROLE_LABELS.get(annotation.role_type, annotation.role_type)


def serialize_annotation(annotation):
    palette = _palette_for(annotation.color_token or annotation.role_type)
    return {
        "id": annotation.id,
        "text_span": annotation.text_span,
        "start_index": annotation.start_index,
        "end_index": annotation.end_index,
        "role_type": annotation.role_type,
        "role_label": ROLE_LABELS.get(annotation.role_type, annotation.role_type),
        "grammar_label": _annotation_label(annotation),
        "explanation": annotation.explanation,
        "color_token": annotation.color_token or annotation.role_type,
        "background": palette["bg"],
        "color": palette["color"],
        "is_core": annotation.is_core,
    }


def _build_segments(sentence_text, annotations, core_only=False):
    result = []
    cursor = 0
    ordered_annotations = sorted(annotations, key=lambda item: (item.start_index, item.sort_order, item.id))
    for annotation in ordered_annotations:
        if annotation.start_index > cursor:
            result.append(
                {
                    "text": sentence_text[cursor:annotation.start_index],
                    "annotation_id": None,
                    "token": "plain",
                    "background": COLOR_PALETTE["plain"]["bg"],
                    "color": COLOR_PALETTE["plain"]["color"],
                    "role_label": "",
                    "grammar_label": "",
                }
            )
        palette_token = annotation.color_token or annotation.role_type
        palette = _palette_for(palette_token)
        if core_only and not annotation.is_core:
            result.append(
                {
                    "text": sentence_text[annotation.start_index:annotation.end_index],
                    "annotation_id": None,
                    "token": "plain",
                    "background": COLOR_PALETTE["plain"]["bg"],
                    "color": COLOR_PALETTE["plain"]["color"],
                    "role_label": "",
                    "grammar_label": "",
                }
            )
        else:
            result.append(
                {
                    "text": sentence_text[annotation.start_index:annotation.end_index],
                    "annotation_id": annotation.id,
                    "token": palette_token,
                    "background": palette["bg"],
                    "color": palette["color"],
                    "role_label": ROLE_LABELS.get(annotation.role_type, annotation.role_type),
                    "grammar_label": _annotation_label(annotation),
                }
            )
        cursor = annotation.end_index

    if cursor < len(sentence_text):
        result.append(
            {
                "text": sentence_text[cursor:],
                "annotation_id": None,
                "token": "plain",
                "background": COLOR_PALETTE["plain"]["bg"],
                "color": COLOR_PALETTE["plain"]["color"],
                "role_label": "",
                "grammar_label": "",
            }
        )

    return [item for item in result if item["text"]]


def _resolve_practice(sentence):
    point = sentence.point
    return {
        "type": sentence.practice_type or "choice",
        "prompt": sentence.practice_prompt or point.practice_prompt,
        "options": sentence.practice_options or point.practice_options,
        "answer": sentence.practice_answer or point.practice_answer,
        "explanation": sentence.practice_explanation or point.practice_explanation,
    }


def _latest_progress_map(user, sentence_ids):
    if not sentence_ids:
        return {}
    records = (
        GrammarLearningRecord.objects.filter(user=user, sentence_id__in=sentence_ids)
        .order_by("sentence_id", "-occurred_at", "-id")
    )
    progress_map = {}
    practice_count = defaultdict(int)
    correct_count = defaultdict(int)
    max_mastery = defaultdict(int)
    bookmarked = defaultdict(bool)

    for record in records:
        practice_count[record.sentence_id] += 1 if record.action_type == "practice" else 0
        correct_count[record.sentence_id] += 1 if record.action_type == "practice" and record.result == "correct" else 0
        max_mastery[record.sentence_id] = max(max_mastery[record.sentence_id], record.mastery_level)
        if record.action_type == "bookmark":
            bookmarked[record.sentence_id] = True
        if record.sentence_id not in progress_map:
            progress_map[record.sentence_id] = {
                "last_action": record.action_type,
                "mastery_level": record.mastery_level,
                "occurred_at": record.occurred_at,
            }

    for sentence_id in sentence_ids:
        base = progress_map.get(
            sentence_id,
            {"last_action": "", "mastery_level": 0, "occurred_at": None},
        )
        base.update(
            {
                "mastery_level": max(base.get("mastery_level", 0), max_mastery.get(sentence_id, 0)),
                "practice_total": practice_count.get(sentence_id, 0),
                "correct_total": correct_count.get(sentence_id, 0),
                "is_bookmarked": bookmarked.get(sentence_id, False),
            }
        )
        progress_map[sentence_id] = base
    return progress_map


def _serialize_sentence_card(sentence, progress=None):
    return {
        "id": sentence.id,
        "sentence": sentence.sentence,
        "translation_cn": sentence.translation_cn,
        "summary": sentence.summary,
        "main_structure": sentence.main_structure,
        "difficulty": sentence.difficulty,
        "difficulty_label": _difficulty_label(sentence.difficulty),
        "scene_tag": sentence.scene_tag,
        "grammar_tags": sentence.grammar_tags or [],
        "is_long_sentence": sentence.is_long_sentence,
        "point": {
            "id": sentence.point_id,
            "title": sentence.point.title,
            "code": sentence.point.code,
            "category": sentence.point.category,
        },
        "progress": progress
        or {
            "last_action": "",
            "mastery_level": 0,
            "practice_total": 0,
            "correct_total": 0,
            "is_bookmarked": False,
            "occurred_at": None,
        },
    }


def list_points(user):
    points = list(GrammarPoint.objects.filter(status="active").order_by("sort_order", "id"))
    progress_records = GrammarLearningRecord.objects.filter(user=user).values(
        "point_id",
        "sentence_id",
        "action_type",
        "mastery_level",
    )
    point_studied = defaultdict(set)
    point_mastered = defaultdict(set)
    point_practice_count = defaultdict(int)
    for record in progress_records:
        point_studied[record["point_id"]].add(record["sentence_id"])
        if record["mastery_level"] >= 4:
            point_mastered[record["point_id"]].add(record["sentence_id"])
        if record["action_type"] == "practice":
            point_practice_count[record["point_id"]] += 1

    result = []
    for point in points:
        sentence_count = point.sentences.filter(status="active").count()
        result.append(
            {
                "id": point.id,
                "code": point.code,
                "title": point.title,
                "category": point.category,
                "difficulty": point.difficulty,
                "difficulty_label": _difficulty_label(point.difficulty),
                "description": point.description,
                "learning_tip": point.learning_tip,
                "sentence_count": sentence_count,
                "progress": {
                    "studied_sentence_count": len(point_studied[point.id]),
                    "mastered_sentence_count": len(point_mastered[point.id]),
                    "practice_count": point_practice_count[point.id],
                    "completion_rate": round((len(point_studied[point.id]) / sentence_count) * 100, 2)
                    if sentence_count
                    else 0,
                },
            }
        )
    return result


def list_sentences(user, validated_data):
    queryset = GrammarSentence.objects.select_related("point").filter(status="active", point__status="active")
    point_id = validated_data.get("point_id")
    if point_id:
        queryset = queryset.filter(point_id=point_id)

    difficulty = validated_data.get("difficulty")
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)

    keyword = (validated_data.get("keyword") or "").strip()
    if keyword:
        queryset = queryset.filter(
            Q(sentence__icontains=keyword)
            | Q(translation_cn__icontains=keyword)
            | Q(summary__icontains=keyword)
            | Q(point__title__icontains=keyword)
        )

    scene_tag = (validated_data.get("scene_tag") or "").strip()
    if scene_tag:
        queryset = queryset.filter(scene_tag__icontains=scene_tag)

    if validated_data.get("is_long_sentence") is True:
        queryset = queryset.filter(is_long_sentence=True)

    queryset = queryset.order_by("point__sort_order", "order_in_point", "id")
    items, total, page, page_size = paginate_queryset(queryset, validated_data["page"], validated_data["page_size"])
    sentence_ids = [item.id for item in items]
    progress_map = _latest_progress_map(user, sentence_ids)
    return {
        "list": [_serialize_sentence_card(item, progress_map.get(item.id)) for item in items],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }


def get_sentence_detail(user, sentence_id):
    sentence = (
        GrammarSentence.objects.select_related("point")
        .prefetch_related("annotations")
        .filter(id=sentence_id, status="active", point__status="active")
        .first()
    )
    if not sentence:
        return None

    annotations = list(sentence.annotations.all().order_by("sort_order", "start_index", "id"))
    progress = _latest_progress_map(user, [sentence.id]).get(
        sentence.id,
        {
            "last_action": "",
            "mastery_level": 0,
            "practice_total": 0,
            "correct_total": 0,
            "is_bookmarked": False,
            "occurred_at": None,
        },
    )
    base_queryset = GrammarSentence.objects.filter(point=sentence.point, status="active").order_by("order_in_point", "id")
    previous_sentence = base_queryset.filter(order_in_point__lt=sentence.order_in_point).last()
    next_sentence = base_queryset.filter(order_in_point__gt=sentence.order_in_point).first()

    return {
        **_serialize_sentence_card(sentence, progress),
        "analysis": sentence.analysis,
        "legend": build_legend(),
        "annotations": [serialize_annotation(item) for item in annotations],
        "complete_segments": _build_segments(sentence.sentence, annotations, core_only=False),
        "core_segments": _build_segments(sentence.sentence, annotations, core_only=True),
        "chunk_breakdown": sentence.chunk_breakdown or [],
        "practice": _resolve_practice(sentence),
        "point_detail": {
            "id": sentence.point_id,
            "title": sentence.point.title,
            "category": sentence.point.category,
            "description": sentence.point.description,
            "learning_tip": sentence.point.learning_tip,
            "difficulty": sentence.point.difficulty,
            "difficulty_label": _difficulty_label(sentence.point.difficulty),
        },
        "navigation": {
            "previous_sentence_id": previous_sentence.id if previous_sentence else None,
            "next_sentence_id": next_sentence.id if next_sentence else None,
        },
    }


def list_recommendations(user, point_id=None, current_sentence_id=None, limit=6):
    queryset = GrammarSentence.objects.select_related("point").filter(status="active", point__status="active")

    if point_id:
        queryset = queryset.filter(point_id=point_id)

    if current_sentence_id:
        current_sentence = GrammarSentence.objects.filter(id=current_sentence_id).first()
        if current_sentence:
            same_point = queryset.filter(point_id=current_sentence.point_id, order_in_point__gt=current_sentence.order_in_point)
            same_point_items = list(same_point.order_by("order_in_point", "id")[:limit])
            if len(same_point_items) >= limit:
                progress_map = _latest_progress_map(user, [item.id for item in same_point_items])
                return [_serialize_sentence_card(item, progress_map.get(item.id)) for item in same_point_items]

    items = list(queryset.order_by("is_long_sentence", "point__sort_order", "order_in_point", "id")[:limit])
    progress_map = _latest_progress_map(user, [item.id for item in items])
    return [_serialize_sentence_card(item, progress_map.get(item.id)) for item in items]


def _infer_mastery_level(validated_data):
    if "mastery_level" in validated_data:
        return validated_data["mastery_level"]

    action_type = validated_data["action_type"]
    result = validated_data.get("result", "")
    if action_type == "understood":
        return 4
    if action_type == "unclear":
        return 1
    if action_type == "bookmark":
        return 3
    if action_type == "practice":
        return 4 if result == "correct" else 2
    return 1


def create_learning_record(user, validated_data):
    sentence = GrammarSentence.objects.select_related("point").filter(id=validated_data["sentence_id"], status="active").first()
    if not sentence:
        raise ValueError("sentence not found")

    record = GrammarLearningRecord.objects.create(
        user=user,
        sentence=sentence,
        point=sentence.point,
        action_type=validated_data["action_type"],
        practice_type=validated_data.get("practice_type", ""),
        result=validated_data.get("result", ""),
        duration=validated_data.get("duration", 0),
        mastery_level=_infer_mastery_level(validated_data),
        extra_payload=validated_data.get("extra_payload", {}),
        occurred_at=validated_data.get("occurred_at") or timezone.now(),
    )
    return {
        "record_id": record.id,
        "sentence_id": sentence.id,
        "progress": _latest_progress_map(user, [sentence.id]).get(sentence.id),
    }


def build_progress(user):
    records = list(
        GrammarLearningRecord.objects.filter(user=user)
        .select_related("point", "sentence")
        .order_by("-occurred_at", "-id")
    )
    total_sentences = GrammarSentence.objects.filter(status="active", point__status="active").count()
    studied_sentences = set()
    practiced_sentences = set()
    mastered_sentences = set()
    topic_progress = defaultdict(lambda: {"studied": set(), "mastered": set(), "practice_count": 0})
    recent_records = []

    for record in records:
        studied_sentences.add(record.sentence_id)
        topic_progress[record.point_id]["studied"].add(record.sentence_id)
        if record.action_type == "practice":
            practiced_sentences.add(record.sentence_id)
            topic_progress[record.point_id]["practice_count"] += 1
        if record.mastery_level >= 4:
            mastered_sentences.add(record.sentence_id)
            topic_progress[record.point_id]["mastered"].add(record.sentence_id)
        if len(recent_records) < 8:
            recent_records.append(
                {
                    "id": record.id,
                    "action_type": record.action_type,
                    "result": record.result,
                    "mastery_level": record.mastery_level,
                    "occurred_at": record.occurred_at,
                    "point_title": record.point.title,
                    "sentence_id": record.sentence_id,
                    "sentence": record.sentence.sentence,
                    "translation_cn": record.sentence.translation_cn,
                }
            )

    points = GrammarPoint.objects.filter(status="active").order_by("sort_order", "id")
    topic_list = []
    for point in points:
        sentence_count = point.sentences.filter(status="active").count()
        topic_list.append(
            {
                "point_id": point.id,
                "point_title": point.title,
                "sentence_count": sentence_count,
                "studied_sentence_count": len(topic_progress[point.id]["studied"]),
                "mastered_sentence_count": len(topic_progress[point.id]["mastered"]),
                "practice_count": topic_progress[point.id]["practice_count"],
                "completion_rate": round((len(topic_progress[point.id]["studied"]) / sentence_count) * 100, 2)
                if sentence_count
                else 0,
            }
        )

    return {
        "total_sentence_count": total_sentences,
        "studied_sentence_count": len(studied_sentences),
        "practiced_sentence_count": len(practiced_sentences),
        "mastered_sentence_count": len(mastered_sentences),
        "total_practice_count": sum(1 for item in records if item.action_type == "practice"),
        "learning_percent": round((len(studied_sentences) / total_sentences) * 100, 2) if total_sentences else 0,
        "recent_records": recent_records,
        "topic_progress": topic_list,
    }
