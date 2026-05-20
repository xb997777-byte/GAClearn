import json
import os
import re
from collections import Counter
from datetime import timedelta
from typing import Dict

from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.books.models import Word
from apps.grammar.models import GrammarPoint, GrammarSentence
from apps.grammar.services import DIFFICULTY_LABELS
from apps.learn.models import WordProgress

from .providers.deepseek import chat_json, is_provider_ready
from .rag.chroma_runtime import chroma_available, get_chroma_runtime, search_knowledge_base
from .rag.personalized_runtime import search_personalized_knowledge
from .rag.retrieval_runtime import build_retrieval_strategy, load_vector_documents, rerank_documents
from .rag.retrievers import extract_query_keywords
from .rag.vector_runtime import LocalHashVectorStore, get_vector_runtime
from .tools.study_tools import build_study_coach_bundle
from .observability import fit_model_char_value


PROMPT_VERSION = "assistant_v1"
SENTENCE_PATTERN = re.compile(r"[^.!?。！？]+[.!?。！？]?")
TECH_QUERY_HINTS = {
    "mac",
    "windows",
    "conda",
    "mysql",
    "django",
    "python",
    "chroma",
    "rag",
    "embedding",
    "index",
    "rebuild",
    "api",
    "mcp",
    "server",
    "接口",
    "后端",
    "前端",
    "数据库",
    "迁移",
    "环境",
    "索引",
    "向量库",
}
PRODUCT_QUERY_HINTS = {
    "ai 自适应计划",
    "应用这份 ai 调整",
    "今天的学习计划",
    "学习计划页",
    "计划页",
    "manifest",
    "tools/call",
    "tool call",
}
PLAN_FLOW_HINTS = {"应用", "按钮", "页面", "入口", "刷新", "滚动", "跳转"}
LEARNING_QUERY_HINTS = ["区别", "怎么区分", "例句", "语法", "近义", "意思", "用法", "单词", "句子", "表达"]
SCENARIO_TEMPLATE_MAP = {
    "daily": {
        "label": "日常交流",
        "difficulty": "基础",
        "mission": "和 AI 做 2 到 3 轮轻松日常对话，重点练习自然回应。",
        "coach_focus": "先用完整句表达，再慢慢增加细节。",
        "assistant_role": "友好的英语聊天伙伴",
        "learner_role": "想提高口语表达的学习者",
        "starters": [
            "Hi, I want to practice speaking English with you.",
            "How was your day today?",
            "I usually study English after dinner.",
        ],
    },
    "restaurant": {
        "label": "餐厅点餐",
        "difficulty": "基础",
        "mission": "完成点餐、追加需求和结账三个环节。",
        "coach_focus": "多用礼貌表达和数量表达。",
        "assistant_role": "餐厅服务员",
        "learner_role": "顾客",
        "starters": [
            "Hello, I would like to order a coffee and a sandwich.",
            "Could I see the menu, please?",
            "Do you have any vegetarian options?",
        ],
    },
    "classroom": {
        "label": "课堂提问",
        "difficulty": "基础",
        "mission": "围绕作业、概念不懂和请老师重复说明完成 2 轮提问。",
        "coach_focus": "练习提问句和确认理解。",
        "assistant_role": "英语老师",
        "learner_role": "课堂上的学生",
        "starters": [
            "Excuse me, could you explain this grammar point again?",
            "I do not understand the homework requirement.",
            "Can I ask one more question about this sentence?",
        ],
    },
    "interview": {
        "label": "面试沟通",
        "difficulty": "进阶",
        "mission": "完成自我介绍、项目经历和优势表达。",
        "coach_focus": "回答要简洁，先结论后举例。",
        "assistant_role": "英文面试官",
        "learner_role": "求职者",
        "starters": [
            "Let me briefly introduce myself.",
            "One of my strengths is learning quickly.",
            "In my last project, I worked on the backend API.",
        ],
    },
    "travel": {
        "label": "旅行问路",
        "difficulty": "基础",
        "mission": "完成问路、确认方向和补充需求。",
        "coach_focus": "练习地点、方向和时间表达。",
        "assistant_role": "当地路人",
        "learner_role": "旅行者",
        "starters": [
            "Excuse me, how can I get to the train station?",
            "Is it far from here?",
            "Should I take the bus or walk there?",
        ],
    },
    "shopping": {
        "label": "购物咨询",
        "difficulty": "基础",
        "mission": "完成询价、试穿和付款咨询。",
        "coach_focus": "练习颜色、尺寸和价格表达。",
        "assistant_role": "商店店员",
        "learner_role": "顾客",
        "starters": [
            "Do you have this in a larger size?",
            "How much is this shirt?",
            "Can I try this on?",
        ],
    },
    "hotel": {
        "label": "酒店入住",
        "difficulty": "进阶",
        "mission": "完成入住登记、房间需求和退房咨询。",
        "coach_focus": "练习预订、证件和时间表达。",
        "assistant_role": "酒店前台",
        "learner_role": "住客",
        "starters": [
            "Hello, I have a reservation under the name Li.",
            "Could I have a quiet room, please?",
            "What time is breakfast served?",
        ],
    },
    "airport": {
        "label": "机场出行",
        "difficulty": "进阶",
        "mission": "完成值机、登机口确认和行李问题咨询。",
        "coach_focus": "练习航班、行李和时间信息表达。",
        "assistant_role": "机场工作人员",
        "learner_role": "乘客",
        "starters": [
            "Where is the check-in counter for this flight?",
            "What is the gate number for boarding?",
            "My luggage did not arrive.",
        ],
    },
}


def _provider_meta():
    return {
        "ai_enabled": is_provider_ready(),
        "prompt_version": PROMPT_VERSION,
        "model_name": os.getenv("AI_MODEL", "").strip(),
    }


def _get_scenario_template(scenario):
    key = str(scenario or "daily").strip().lower()
    return {"scenario": key, **SCENARIO_TEMPLATE_MAP.get(key, SCENARIO_TEMPLATE_MAP["daily"])}


def list_scenario_templates():
    templates = []
    for scenario, template in SCENARIO_TEMPLATE_MAP.items():
        templates.append(
            {
                "scenario": scenario,
                "label": template["label"],
                "difficulty": template["difficulty"],
                "mission": template["mission"],
                "coach_focus": template["coach_focus"],
                "assistant_role": template["assistant_role"],
                "learner_role": template["learner_role"],
                "starters": template["starters"][:3],
            }
        )
    return templates


def _keyword_query(keywords, fields):
    q = Q()
    for keyword in keywords[:8]:
        for field in fields:
            q |= Q(**{f"{field}__icontains": keyword})
    return q


def _extract_exact_word_targets(text, limit=4):
    targets = []
    for token in re.findall(r"[A-Za-z][A-Za-z-']+", str(text or "")):
        lowered = token.strip().lower()
        if not lowered or len(lowered) <= 2 or lowered in targets:
            continue
        targets.append(lowered)
    return targets[: max(int(limit or 4), 1)]


def _serialize_word(item, reason="", match_quality="keyword"):
    return {
        "id": item.id,
        "word": item.word,
        "meaning_cn": item.meaning_cn,
        "part_of_speech": item.part_of_speech,
        "example_sentence": item.example_sentence,
        "example_translation": item.example_translation,
        "reason": reason,
        "match_quality": match_quality,
    }


def retrieve_learning_context(text, limit=6):
    keywords = extract_query_keywords(text)
    exact_word_targets = _extract_exact_word_targets(text)
    words = []
    sentences = []
    points = []
    exact_word_ids = set()

    if exact_word_targets:
        exact_q = Q()
        for token in exact_word_targets[:6]:
            exact_q |= Q(word__iexact=token)
        exact_rows = list(Word.objects.filter(exact_q).select_related("book").order_by("book_id", "order_in_book", "id"))
        exact_lookup = {item.word.lower(): item for item in exact_rows}
        words.extend(exact_lookup[token] for token in exact_word_targets if token in exact_lookup)
        exact_word_ids = {item.id for item in words}

    if keywords and len(words) < limit:
        word_q = _keyword_query(keywords, ["word", "meaning_cn", "example_sentence", "synonyms"])
        additional_words = list(
            Word.objects.filter(word_q)
            .exclude(id__in=exact_word_ids)
            .select_related("book")
            .order_by("book_id", "order_in_book", "id")[: max(limit * 3, limit)]
        )
        for item in additional_words:
            if len(words) >= limit:
                break
            words.append(item)

        sentence_q = _keyword_query(keywords, ["sentence", "translation_cn", "summary", "analysis", "point__title"])
        sentences = list(
            GrammarSentence.objects.select_related("point")
            .filter(sentence_q, status="active", point__status="active")
            .order_by("point__sort_order", "order_in_point", "id")[:limit]
        )

        point_q = _keyword_query(keywords, ["title", "description", "learning_tip", "category"])
        points = list(GrammarPoint.objects.filter(point_q, status="active").order_by("sort_order", "id")[:limit])

    if not words:
        words = list(Word.objects.select_related("book").order_by("book_id", "order_in_book", "id")[: min(limit, 4)])
    if not sentences and not exact_word_ids:
        sentences = list(
            GrammarSentence.objects.select_related("point")
            .filter(status="active", point__status="active")
            .order_by("difficulty", "point__sort_order", "id")[: min(limit, 4)]
        )
    if not points and not exact_word_ids:
        points = list(GrammarPoint.objects.filter(status="active").order_by("difficulty", "sort_order", "id")[: min(limit, 4)])

    return {
        "keywords": keywords,
        "words": [
            _serialize_word(
                item,
                "直接命中待学习或待区分的单词。" if item.id in exact_word_ids else "命中输入中的关键词或作为基础参考词。",
                "exact" if item.id in exact_word_ids else ("keyword" if keywords else "fallback"),
            )
            for item in words
        ],
        "sentences": [
            {
                "id": item.id,
                "sentence": item.sentence,
                "translation_cn": item.translation_cn,
                "summary": item.summary,
                "point_title": item.point.title,
                "difficulty_label": DIFFICULTY_LABELS.get(item.difficulty, "基础"),
            }
            for item in sentences
        ],
        "grammar_points": [
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "difficulty_label": DIFFICULTY_LABELS.get(item.difficulty, "基础"),
                "description": item.description,
                "learning_tip": item.learning_tip,
            }
            for item in points
        ],
    }


def classify_query_intent(query: str) -> Dict[str, object]:
    text = str(query or "").strip()
    lowered = text.lower()
    tech_hits = []
    for token in TECH_QUERY_HINTS:
        if token.lower() in lowered:
            tech_hits.append(token)
    product_hits = [token for token in PRODUCT_QUERY_HINTS if token in lowered]
    learning_hits = [item for item in LEARNING_QUERY_HINTS if item in text]
    plan_flow_query = (
        ("计划" in text and any(token in text for token in PLAN_FLOW_HINTS))
        or "ai 自适应计划" in lowered
        or "应用这份 ai 调整" in lowered
    )
    is_tech = (
        len(tech_hits) >= 2
        or ("怎么" in text and any(item in lowered for item in ["rebuild", "index", "conda", "mcp", "mysql", "manifest"]))
        or bool(product_hits)
        or plan_flow_query
    )
    if is_tech and len(learning_hits) <= 1:
        reason_hits = tech_hits[:4] + product_hits[:3]
        if plan_flow_query:
            reason_hits.append("计划应用流程")
        return {
            "intent": "tech",
            "label": "技术/产品问题",
            "allowed_audiences": ["dev", "migration", "product"],
            "reason": f"检测到技术/产品关键词：{' / '.join(list(dict.fromkeys(reason_hits))[:6])}" if reason_hits else "问题更偏项目功能、接口或页面流程。",
        }
    return {
        "intent": "learning",
        "label": "学习问题",
        "allowed_audiences": ["learning"],
        "reason": "默认优先从词库、语法库、例句库和学习资料中回答。",
    }


def normalize_learning_query(query: str) -> Dict[str, object]:
    raw = str(query or "").strip()
    compact = " ".join(raw.split())
    expansions = []
    lowered = compact.lower()
    if "怎么区分" in compact or "区别" in compact:
        expansions.extend(["difference", "usage", "example"])
    if any(token in compact for token in ["近义", "同义", "相近"]):
        expansions.extend(["synonym", "similar usage"])
    if any(token in compact for token in ["例句", "造句"]):
        expansions.append("example sentence")
    if any(token in compact for token in ["语法", "句型"]):
        expansions.extend(["grammar rule", "sentence pattern"])
    english_words = re.findall(r"[A-Za-z][A-Za-z-']+", compact)
    if len(english_words) == 2 and ("区别" in compact or "怎么区分" in compact):
        compact = f"{english_words[0]} 和 {english_words[1]} 怎么区分？请给词义区别、常见搭配和例句。"
    elif len(compact) <= 12 and english_words:
        compact = f"{compact}。请结合词义、常见搭配和例句回答。"
    deduped = []
    for item in expansions:
        token = str(item or "").strip()
        if token and token not in deduped:
            deduped.append(token)
    return {
        "raw_query": raw,
        "normalized_query": compact or raw,
        "query_expansions": deduped[:6],
    }


def _split_sentences(text):
    result = []
    for item in SENTENCE_PATTERN.findall(text or ""):
        sentence = item.strip()
        if sentence:
            result.append(sentence)
    return result[:12] or [text.strip()]


def _build_writing_fallback(text, context):
    sentences = _split_sentences(text)
    corrected_sentences = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if cleaned:
            corrected_sentences.append(cleaned[0].upper() + cleaned[1:])
    corrected_text = " ".join(corrected_sentences)
    suggestions = [
        "先检查主谓是否完整，再看时态是否统一。",
        "把过长的句子拆成两句，表达会更清楚。",
        "优先使用你已经学过的高频词，减少不确定表达。",
    ]
    if context.get("grammar_points"):
        suggestions[0] = f"可以重点回看“{context['grammar_points'][0]['title']}”，它和这段文本的表达关系较近。"
    return {
        "score": 78,
        "level": "可理解，但还可以更自然",
        "corrected_text": corrected_text,
        "overall_feedback": "这段表达基本能传达意思。当前版本会先给出规则型建议；配置 AI 后会给出更细的逐句批改。",
        "sentence_feedback": [
            {
                "original": sentence,
                "corrected": corrected_sentences[index] if index < len(corrected_sentences) else sentence,
                "issue": "建议检查语法结构、词汇搭配和标点。",
                "explanation": "先确保句子主干清楚，再补充修饰成分。",
            }
            for index, sentence in enumerate(sentences)
        ],
        "suggestions": suggestions,
        "linked_grammar_points": context.get("grammar_points", [])[:3],
        "useful_expressions": [item["word"] for item in context.get("words", [])[:4]],
    }


def correct_writing(user, text, level="cet4"):
    context = retrieve_learning_context(text)
    if not is_provider_ready():
        result = _build_writing_fallback(text, context)
    else:
        payload = {
            "text": text,
            "target_level": level,
            "retrieved_context": context,
            "task": "Correct this English writing for a Chinese learner. Return strict JSON only.",
            "output_schema": {
                "score": 0,
                "level": "string",
                "corrected_text": "string",
                "overall_feedback": "string",
                "sentence_feedback": [
                    {
                        "original": "string",
                        "corrected": "string",
                        "issue": "string",
                        "explanation": "string",
                    }
                ],
                "suggestions": ["string"],
                "linked_grammar_points": [{"id": 0, "title": "string", "description": "string"}],
                "useful_expressions": ["string"],
            },
        }
        fallback = _build_writing_fallback(text, context)
        try:
            ai_result = chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an English writing correction teacher for Chinese learners. "
                            "Stay practical, cite provided grammar context when useful, and return strict JSON only."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                ],
                temperature=0.2,
            )
            fallback.update({key: ai_result.get(key) or fallback[key] for key in fallback})
        except Exception as exc:
            fallback["provider_error"] = str(exc)
        result = fallback
    return {
        "headline": "AI 写作批改",
        "summary": result.get("overall_feedback", ""),
        "result": result,
        "retrieval": context,
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": _provider_meta(),
    }


def _build_writing_prompt_fallback(level, topic, genre, context):
    topic_text = topic or "daily English learning"
    linked_words = context.get("words", [])[:5]
    expressions = []
    for word in linked_words:
        if word.get("word"):
            expressions.append(f"{word['word']} - {word.get('meaning_cn', '')}")
    if not expressions:
        expressions = ["keep a steady pace", "make progress", "learn from mistakes"]
    sample_topic = topic_text if topic else "How to make English learning part of daily life"
    sample_essay = (
        f"{sample_topic}\n\n"
        "Learning English is not only about remembering words. It is also about using them in real situations. "
        "For me, a good method is to review old words first and then learn a few new ones every day. "
        "When I meet a difficult expression, I write it down and make my own sentence. "
        "This habit helps me understand the meaning more clearly and remember it for a longer time. "
        "Although progress may be slow at the beginning, steady practice can make English learning easier and more enjoyable."
    )
    return {
        "title": f"{level.upper()} 写作题",
        "prompt": f"Write a {genre or 'short essay'} about: {sample_topic}.",
        "level": level,
        "genre": genre or "essay",
        "writing_goals": [
            "观点明确，开头直接回应题目。",
            "每段只展开一个核心意思。",
            "尽量使用熟悉词汇，保证语法稳定。",
        ],
        "outline": [
            {"section": "开头", "guidance": "用一句话点明你的立场或主题。"},
            {"section": "主体", "guidance": "给出 2 个理由，并各配一个简单例子。"},
            {"section": "结尾", "guidance": "总结观点，补一句行动或建议。"},
        ],
        "sample_essay": sample_essay,
        "scoring_rubric": [
            {"dimension": "内容", "points": "30%", "focus": "是否完整回应题目。"},
            {"dimension": "结构", "points": "25%", "focus": "段落是否清晰，衔接是否自然。"},
            {"dimension": "语言", "points": "30%", "focus": "语法、拼写、搭配是否稳定。"},
            {"dimension": "表达", "points": "15%", "focus": "是否有自然表达和个人观点。"},
        ],
        "useful_expressions": expressions,
        "linked_words": linked_words,
        "linked_grammar_points": context.get("grammar_points", [])[:3],
    }


def generate_writing_prompt(user, level="cet4", topic="", genre="essay"):
    context = retrieve_learning_context(topic or genre or level, limit=6)
    fallback = _build_writing_prompt_fallback(level, topic, genre, context)
    if is_provider_ready():
        payload = {
            "level": level,
            "topic": topic,
            "genre": genre,
            "retrieved_context": context,
            "task": "Generate an English writing prompt, outline, sample essay, rubric and expressions for a Chinese learner. Return strict JSON only.",
            "output_schema": {
                "title": "string",
                "prompt": "string",
                "level": "string",
                "genre": "string",
                "writing_goals": ["string"],
                "outline": [{"section": "string", "guidance": "string"}],
                "sample_essay": "string",
                "scoring_rubric": [{"dimension": "string", "points": "string", "focus": "string"}],
                "useful_expressions": ["string"],
                "linked_words": [{"word": "string", "meaning_cn": "string"}],
                "linked_grammar_points": [{"id": 0, "title": "string"}],
            },
        }
        try:
            ai_result = chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an English writing exam coach for Chinese learners. "
                            "Use provided learning context and return strict JSON only."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                ],
                temperature=0.35,
            )
            fallback.update({key: ai_result.get(key) or fallback[key] for key in fallback})
        except Exception as exc:
            fallback["provider_error"] = str(exc)
    return {
        "headline": fallback.get("title", "AI 写作题目生成"),
        "summary": fallback.get("prompt", ""),
        "result": fallback,
        "retrieval": context,
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": _provider_meta(),
    }


def _detect_translation_direction(source_text, target_text):
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", source_text or ""))
    english_chars = len(re.findall(r"[A-Za-z]", source_text or ""))
    if chinese_chars > english_chars:
        return "zh_to_en"
    if target_text and len(re.findall(r"[\u4e00-\u9fff]", target_text)) > len(re.findall(r"[A-Za-z]", target_text)):
        return "en_to_zh"
    return "en_to_zh" if english_chars else "zh_to_en"


def _build_translation_fallback(source_text, user_translation, direction, context):
    reference = ""
    if context.get("sentences"):
        first = context["sentences"][0]
        reference = first["sentence"] if direction == "zh_to_en" else first["translation_cn"]
    if not reference:
        reference = "请配置 AI 后获取更自然的参考译文。"
    return {
        "direction": direction,
        "score": 72 if user_translation else 0,
        "reference_translation": reference,
        "feedback": "当前先基于项目语料给出参考方向；配置 AI 后会细分准确性、自然度和语法问题。",
        "accuracy_notes": ["检查核心意思是否完整保留。"],
        "naturalness_notes": ["译文尽量使用自然短句，不要逐词硬翻。"],
        "grammar_notes": ["注意时态、单复数和介词搭配。"],
        "alternative_expressions": [item["sentence"] for item in context.get("sentences", [])[:3]],
        "linked_words": context.get("words", [])[:4],
    }


def evaluate_translation(user, source_text, user_translation="", direction="auto"):
    resolved_direction = direction if direction in {"zh_to_en", "en_to_zh"} else _detect_translation_direction(source_text, user_translation)
    context = retrieve_learning_context(f"{source_text} {user_translation}")
    if not is_provider_ready():
        result = _build_translation_fallback(source_text, user_translation, resolved_direction, context)
    else:
        payload = {
            "source_text": source_text,
            "user_translation": user_translation,
            "direction": resolved_direction,
            "retrieved_context": context,
            "task": "Evaluate or generate a translation exercise answer for a Chinese English learner. Return strict JSON only.",
            "output_schema": {
                "direction": "string",
                "score": 0,
                "reference_translation": "string",
                "feedback": "string",
                "accuracy_notes": ["string"],
                "naturalness_notes": ["string"],
                "grammar_notes": ["string"],
                "alternative_expressions": ["string"],
                "linked_words": [{"word": "string", "meaning_cn": "string"}],
            },
        }
        fallback = _build_translation_fallback(source_text, user_translation, resolved_direction, context)
        try:
            ai_result = chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a bilingual translation coach for Chinese learners of English. "
                            "Give concise feedback and return strict JSON only."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                ],
                temperature=0.2,
            )
            fallback.update({key: ai_result.get(key) or fallback[key] for key in fallback})
        except Exception as exc:
            fallback["provider_error"] = str(exc)
        result = fallback
    return {
        "headline": "AI 翻译训练",
        "summary": result.get("feedback", ""),
        "result": result,
        "retrieval": context,
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": _provider_meta(),
    }


def _serialize_ai_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "payload": message.payload,
        "created_at": message.created_at,
    }


def _serialize_ai_conversation(conversation):
    return {
        "id": conversation.id,
        "feature_type": conversation.feature_type,
        "title": conversation.title,
        "context": conversation.context,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def _scenario_label(scenario):
    return _get_scenario_template(scenario)["label"]


def _build_scenario_fallback(scenario, user_message, context):
    template = _get_scenario_template(scenario)
    label = template["label"]
    words = context.get("words", [])[:4]
    vocabulary = [
        {
            "word": item.get("word", ""),
            "meaning_cn": item.get("meaning_cn", ""),
            "example": item.get("example_sentence", ""),
        }
        for item in words
        if item.get("word")
    ]
    if not vocabulary:
        vocabulary = [
            {"word": "Could you ...?", "meaning_cn": "你能……吗？", "example": "Could you help me with this?"},
            {"word": "I would like ...", "meaning_cn": "我想要……", "example": "I would like a cup of tea."},
        ]
    return {
        "scenario": scenario,
        "scenario_label": label,
        "mission": template["mission"],
        "coach_focus": template["coach_focus"],
        "role_card": {
            "assistant_role": template["assistant_role"],
            "learner_role": template["learner_role"],
        },
        "assistant_reply": f"Great. In the {label} scene, you can continue like this: {template['starters'][0]}",
        "correction": {
            "corrected": user_message.strip(),
            "notes": [template["coach_focus"], "先保证句子主干完整，再补充礼貌表达。"],
        },
        "next_suggestions": template["starters"][1:] + ["Could you say that again, please?"],
        "starter_examples": template["starters"][:3],
        "vocabulary": vocabulary,
        "scenario_progress": "已完成一次文本对话轮次，可以继续输入下一句。",
    }


def run_scenario_dialogue(user, scenario, user_message, conversation_id=None):
    from .models import AIConversation, AIMessage

    scenario = scenario or "daily"
    if conversation_id:
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=user)
    else:
        conversation = AIConversation.objects.create(
            user=user,
            feature_type="scenario",
            title=f"{_scenario_label(scenario)}对话",
            context={"scenario": scenario, "source": "scenario_dialogue"},
        )

    recent_messages = list(conversation.messages.order_by("-id")[:8])
    history = [{"role": item.role, "content": item.content} for item in reversed(recent_messages)]
    user_record = AIMessage.objects.create(conversation=conversation, role="user", content=user_message)
    context = retrieve_learning_context(f"{scenario} {user_message}", limit=6)
    result = _build_scenario_fallback(scenario, user_message, context)
    if is_provider_ready():
        payload = {
            "scenario": scenario,
            "scenario_label": _scenario_label(scenario),
            "template": _get_scenario_template(scenario),
            "user_message": user_message,
            "history": history,
            "retrieved_context": context,
            "task": "Continue a text-only English scenario dialogue and coach the learner. Return strict JSON only.",
            "output_schema": {
                "scenario": "string",
                "scenario_label": "string",
                "mission": "string",
                "coach_focus": "string",
                "role_card": {"assistant_role": "string", "learner_role": "string"},
                "assistant_reply": "string",
                "correction": {"corrected": "string", "notes": ["string"]},
                "next_suggestions": ["string"],
                "starter_examples": ["string"],
                "vocabulary": [{"word": "string", "meaning_cn": "string", "example": "string"}],
                "scenario_progress": "string",
            },
        }
        try:
            ai_result = chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a text-only English scenario dialogue partner. "
                            "Do not evaluate pronunciation. Keep replies short and useful. Return strict JSON only."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                ],
                temperature=0.35,
            )
            result.update({key: ai_result.get(key) or result[key] for key in result})
        except Exception as exc:
            result["provider_error"] = str(exc)
    assistant_record = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=result.get("assistant_reply", ""),
        payload={"result": result, "retrieval": context},
        prompt_version=fit_model_char_value(
            PROMPT_VERSION,
            AIMessage._meta.get_field("prompt_version").max_length,
        ),
        model_name=fit_model_char_value(
            _provider_meta().get("model_name", ""),
            AIMessage._meta.get_field("model_name").max_length,
        ),
    )
    return {
        "headline": result.get("scenario_label", "AI 情景对话"),
        "summary": result.get("assistant_reply", ""),
        "conversation": _serialize_ai_conversation(conversation),
        "user_message": _serialize_ai_message(user_record),
        "assistant_message": _serialize_ai_message(assistant_record),
        "result": result,
        "retrieval": context,
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": _provider_meta(),
    }


def _build_structured_recall_items(context):
    items = []
    for item in context.get("words", []) or []:
        items.append(
            {
                "source_type": "word",
                "title": item.get("word", ""),
                "text": " ".join([item.get("word", ""), item.get("meaning_cn", ""), item.get("example_sentence", "")]),
            }
        )
    for item in context.get("grammar_points", []) or []:
        items.append(
            {
                "source_type": "grammar_point",
                "title": item.get("title", ""),
                "text": " ".join([item.get("title", ""), item.get("description", ""), item.get("learning_tip", "")]),
            }
        )
    for item in context.get("sentences", []) or []:
        items.append(
            {
                "source_type": "grammar_sentence",
                "title": item.get("sentence", "")[:80],
                "text": " ".join([item.get("sentence", ""), item.get("translation_cn", ""), item.get("summary", "")]),
            }
        )
    return items


def _keyword_hit_summary(items, expected_keywords, preferred_source_type=""):
    expected_keywords = [item for item in expected_keywords if item]
    coverage = []
    preferred_hits = 0
    for keyword in expected_keywords:
        matched_sources = []
        for item in items:
            if keyword.lower() in str(item.get("text", "")).lower():
                matched_sources.append(item.get("source_type", ""))
                if preferred_source_type and item.get("source_type") == preferred_source_type:
                    preferred_hits += 1
        coverage.append(
            {
                "keyword": keyword,
                "hit": bool(matched_sources),
                "matched_sources": list(dict.fromkeys(matched_sources)),
            }
        )
    hit_count = sum(1 for item in coverage if item["hit"])
    return {
        "keyword_hits": coverage,
        "coverage_rate": round((hit_count / len(expected_keywords)) * 100, 2) if expected_keywords else 0,
        "preferred_source_hits": preferred_hits,
    }


def evaluate_rag_recall(query, expected_keywords=None, preferred_source_type="", limit=6, user=None):
    expected_keywords = expected_keywords or extract_query_keywords(query)
    structured = retrieve_learning_context(query, limit=limit)
    structured_items = _build_structured_recall_items(structured)
    vector_docs, _, _, retrieval_runtime = _rank_vector_documents(query, limit=limit, user=user)
    reranked_docs = rerank_documents(query, vector_docs, expected_keywords, limit=limit)
    vector_items = [
        {
            "source_type": item.get("source_type", ""),
            "title": item.get("title", ""),
            "text": " ".join([item.get("title", ""), item.get("content_preview", ""), item.get("content", "")]),
            "score": item.get("rerank_score", item.get("score", 0)),
        }
        for item in reranked_docs
    ]
    structured_summary = _keyword_hit_summary(structured_items, expected_keywords, preferred_source_type=preferred_source_type)
    vector_summary = _keyword_hit_summary(vector_items, expected_keywords, preferred_source_type=preferred_source_type)
    hybrid_docs, _, _, hybrid_runtime = _rank_vector_documents(query, limit=limit, retrieval_mode="hybrid", user=user)
    hybrid_items = [
        {
            "source_type": item.get("source_type", ""),
            "title": item.get("title", ""),
            "text": " ".join([item.get("title", ""), item.get("content_preview", ""), item.get("content", "")]),
            "score": item.get("score", 0),
        }
        for item in hybrid_docs
    ]
    hybrid_summary = _keyword_hit_summary(hybrid_items, expected_keywords, preferred_source_type=preferred_source_type)
    better_strategy = "structured"
    if vector_summary["coverage_rate"] > structured_summary["coverage_rate"]:
        better_strategy = "vector"
    if hybrid_summary["coverage_rate"] > max(structured_summary["coverage_rate"], vector_summary["coverage_rate"]):
        better_strategy = "hybrid"
    diagnosis = "当前检索覆盖稳定。"
    best_rate = max(structured_summary["coverage_rate"], vector_summary["coverage_rate"], hybrid_summary["coverage_rate"])
    if best_rate < 50:
        diagnosis = "当前查询关键词较散，建议补充更具体的词或语法点。"
    elif preferred_source_type and structured_summary["preferred_source_hits"] == 0 and vector_summary["preferred_source_hits"] == 0:
        diagnosis = "当前没有明显命中你偏好的资料类型，可以换成更具体的语法点或单词。"
    return {
        "query": query,
        "expected_keywords": expected_keywords,
        "preferred_source_type": preferred_source_type,
        "better_strategy": better_strategy,
        "diagnosis": diagnosis,
        "structured_recall": {
            "coverage_rate": structured_summary["coverage_rate"],
            "keyword_hits": structured_summary["keyword_hits"],
            "top_hits": structured_items[: min(len(structured_items), 6)],
        },
        "vector_recall": {
            "coverage_rate": vector_summary["coverage_rate"],
            "keyword_hits": vector_summary["keyword_hits"],
            "personalized_hits": int(retrieval_runtime.get("personalized_hits", 0) or 0),
            "top_hits": [
                {
                    "source_type": item["source_type"],
                    "title": item["title"],
                    "score": item.get("score", 0),
                }
                for item in vector_items[: min(len(vector_items), 6)]
            ],
        },
        "hybrid_recall": {
            "coverage_rate": hybrid_summary["coverage_rate"],
            "keyword_hits": hybrid_summary["keyword_hits"],
            "personalized_hits": int(hybrid_runtime.get("personalized_hits", 0) or 0),
            "top_hits": [
                {
                    "source_type": item["source_type"],
                    "title": item["title"],
                    "score": item.get("score", 0),
                }
                for item in hybrid_items[: min(len(hybrid_items), 6)]
            ],
        },
        "retrieval_runtime": {
            "vector": retrieval_runtime,
            "hybrid": hybrid_runtime,
        },
        "recommendations": [
            "把问题里的核心单词、近义词或语法点名称写得更具体。",
            "如果你想找句子示例，可以在问题里直接带一个短句。",
            "先看覆盖率高的一侧，再决定用结构化检索、向量检索还是 hybrid 检索继续追问。",
        ],
        "ai_strategy": _provider_meta(),
    }


def build_grammar_guide(user):
    bundle = build_study_coach_bundle(user, trend_days=7)
    wrong_patterns = bundle.get("wrong_patterns") or []
    weak_labels = [item for item in wrong_patterns if item]
    learned_sentence_ids = set(
        WordProgress.objects.filter(user=user, learn_count__gt=0).values_list("word_id", flat=True)[:20]
    )
    points = list(GrammarPoint.objects.filter(status="active").order_by("difficulty", "sort_order", "id")[:8])
    recommended = []
    for point in points:
        reason = "适合作为当前阶段的语法基础巩固。"
        if weak_labels:
            reason = f"结合近期错词模式，建议用“{point.title}”补一次句子结构意识。"
        first_sentence = (
            GrammarSentence.objects.filter(point=point, status="active")
            .order_by("difficulty", "order_in_point", "id")
            .first()
        )
        recommended.append(
            {
                "point_id": point.id,
                "title": point.title,
                "category": point.category,
                "difficulty_label": DIFFICULTY_LABELS.get(point.difficulty, "基础"),
                "reason": reason,
                "learning_tip": point.learning_tip,
                "sentence_id": first_sentence.id if first_sentence else None,
                "sample_sentence": first_sentence.sentence if first_sentence else "",
            }
        )
    return {
        "headline": "本周语法导学建议",
        "summary": "先用少量高频语法点补足句子理解，再回到单词和例句里巩固。",
        "recommended_points": recommended[:5],
        "weak_patterns": weak_labels,
        "learned_word_ids_sample": list(learned_sentence_ids),
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": _provider_meta(),
    }


def run_rag_search(query, limit=6):
    context = retrieve_learning_context(query, limit=limit)
    answer = _build_rag_answer(query, context)
    return {
        "headline": "AI 检索问答",
        "summary": (answer or {}).get("summary") or "",
        "query": query,
        "answer": answer,
        "retrieval": context,
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": _provider_meta(),
    }


def _highlight_terms(text, keywords, limit=3):
    text = str(text or "").strip()
    highlights = []
    lowered = text.lower()
    for keyword in keywords[:8]:
        token = str(keyword or "").strip()
        if not token:
            continue
        index = lowered.find(token.lower())
        if index < 0:
            continue
        start = max(0, index - 18)
        end = min(len(text), index + len(token) + 26)
        snippet = text[start:end].strip()
        if snippet and snippet not in highlights:
            highlights.append(snippet)
        if len(highlights) >= limit:
            break
    return highlights


def _document_match_reason(item, keywords):
    metadata = item.get("metadata", {}) or {}
    reason = []
    if metadata.get("chunk_kind"):
        reason.append(f"chunk={metadata.get('chunk_kind')}")
    matched = []
    haystack = " ".join(
        [
            str(item.get("title", "")),
            str(item.get("content_preview", "")),
            str(item.get("content", "")),
            str(metadata.get("keyword_hints", "")),
        ]
    ).lower()
    for keyword in keywords[:8]:
        if keyword.lower() in haystack:
            matched.append(keyword)
    if matched:
        reason.append(f"命中关键词：{' / '.join(list(dict.fromkeys(matched))[:4])}")
    if metadata.get("point_title"):
        reason.append(str(metadata.get("point_title")))
    if metadata.get("book_name"):
        reason.append(str(metadata.get("book_name")))
    if metadata.get("section_title") and metadata.get("source_group") == "project_doc":
        reason.append(f"章节：{metadata.get('section_title')}")
    if metadata.get("audience"):
        reason.append(f"audience={metadata.get('audience')}")
    return "；".join(reason)


def _enrich_documents_with_highlights(docs, keywords):
    enriched = []
    for item in docs or []:
        doc = dict(item)
        source_text = " ".join(
            [
                str(doc.get("title", "")),
                str(doc.get("content_preview", "")),
                str(doc.get("content", "")),
            ]
        )
        doc["matched_keywords"] = [keyword for keyword in keywords[:8] if keyword.lower() in source_text.lower()]
        doc["highlights"] = _highlight_terms(source_text, keywords, limit=3)
        doc["match_reason"] = _document_match_reason(doc, keywords)
        enriched.append(doc)
    return enriched


def _to_structured_documents(context):
    docs = []
    for item in context.get("words") or []:
        match_quality = str(item.get("match_quality") or "keyword")
        score = 0.92 if match_quality == "exact" else (0.74 if match_quality == "keyword" else 0.6)
        docs.append(
            {
                "source_type": "word",
                "source_id": item.get("id", 0),
                "title": item.get("word", ""),
                "content": " ".join(
                    [
                        item.get("word", ""),
                        item.get("meaning_cn", ""),
                        item.get("part_of_speech", ""),
                        item.get("example_sentence", ""),
                        item.get("example_translation", ""),
                    ]
                ),
                "content_preview": " ".join(
                    [
                        item.get("meaning_cn", ""),
                        item.get("example_sentence", ""),
                    ]
                )[:240],
                "score": score,
                "metadata": {
                    "reason": item.get("reason", ""),
                    "source": "structured",
                    "audience": "learning",
                    "match_quality": match_quality,
                },
            }
        )
    for item in context.get("grammar_points") or []:
        docs.append(
            {
                "source_type": "grammar_point",
                "source_id": item.get("id", 0),
                "title": item.get("title", ""),
                "content": " ".join(
                    [
                        item.get("title", ""),
                        item.get("category", ""),
                        item.get("description", ""),
                        item.get("learning_tip", ""),
                    ]
                ),
                "content_preview": " ".join(
                    [
                        item.get("description", ""),
                        item.get("learning_tip", ""),
                    ]
                )[:240],
                "score": 0.62,
                "metadata": {
                    "reason": item.get("learning_tip", ""),
                    "source": "structured",
                    "audience": "learning",
                },
            }
        )
    for item in context.get("sentences") or []:
        docs.append(
            {
                "source_type": "grammar_sentence",
                "source_id": item.get("id", 0),
                "title": item.get("sentence", "")[:80],
                "content": " ".join(
                    [
                        item.get("sentence", ""),
                        item.get("translation_cn", ""),
                        item.get("summary", ""),
                        item.get("point_title", ""),
                    ]
                ),
                "content_preview": " ".join(
                    [
                        item.get("sentence", ""),
                        item.get("translation_cn", ""),
                    ]
                )[:240],
                "score": 0.6,
                "metadata": {
                    "reason": item.get("point_title", ""),
                    "source": "structured",
                    "audience": "learning",
                },
            }
        )
    return docs


def _merge_hybrid_documents(structured_docs, vector_docs, limit=8):
    merged = {}
    ordered = []

    def touch(doc, origin):
        key = f"{doc.get('source_type', '')}:{doc.get('source_id', '')}:{doc.get('title', '')}"
        if key not in merged:
            merged[key] = dict(doc)
            existing_sources = list(doc.get("retrieval_sources") or [])
            if origin not in existing_sources:
                existing_sources.append(origin)
            merged[key]["retrieval_sources"] = existing_sources
            ordered.append(key)
            return
        current = merged[key]
        current["score"] = round(max(float(current.get("score", 0) or 0), float(doc.get("score", 0) or 0)), 4)
        for source in list(doc.get("retrieval_sources") or []) + [origin]:
            if source not in current["retrieval_sources"]:
                current["retrieval_sources"].append(source)
        if len(str(doc.get("content_preview", ""))) > len(str(current.get("content_preview", ""))):
            current["content_preview"] = doc.get("content_preview", "")
        if doc.get("content") and len(str(doc.get("content", ""))) > len(str(current.get("content", ""))):
            current["content"] = doc.get("content", "")
        metadata = dict(current.get("metadata") or {})
        metadata.update(doc.get("metadata") or {})
        current["metadata"] = metadata

    for item in structured_docs or []:
        touch(item, "structured")
    for item in vector_docs or []:
        touch(item, "vector")

    rows = [merged[key] for key in ordered]
    rows.sort(
        key=lambda item: (
            -int(str(((item.get("metadata") or {}).get("match_quality")) or "") == "exact"),
            -len(item.get("retrieval_sources", [])),
            -(float(item.get("score", 0) or 0)),
            str(item.get("title", "")),
        )
    )
    return rows[: min(max(int(limit or 8), 1), 12)]


def _rank_vector_documents(query, limit=8, retrieval_mode="hybrid", user=None):
    mode = str(retrieval_mode or "hybrid").strip().lower() or "hybrid"
    if mode == "auto":
        mode = "hybrid"
    query_bundle = normalize_learning_query(query)
    normalized_query = str(query_bundle.get("normalized_query") or query or "").strip()
    query_expansions = query_bundle.get("query_expansions") or []
    structured_context = None
    structured_docs = []
    vector_docs = []
    personalized_docs = []
    using_chroma = False
    personalized_enabled = False
    query_intent = classify_query_intent(normalized_query)
    structured_enabled = query_intent.get("intent") == "learning"

    if mode in {"structured_only", "hybrid"} and structured_enabled:
        structured_context = retrieve_learning_context(normalized_query, limit=limit)
        structured_docs = _to_structured_documents(structured_context)

    if mode in {"vector_only", "hybrid"}:
        vector_query = " ".join([normalized_query] + query_expansions[:4]).strip()
        vector_docs, using_chroma, personalized_docs, backend_name = load_vector_documents(
            vector_query,
            limit=max(limit, 10),
            user=user,
            allowed_audiences=query_intent.get("allowed_audiences") or ["learning"],
        )
        personalized_enabled = bool(personalized_docs)
    else:
        backend_name = ""

    if mode == "structured_only":
        return structured_docs, structured_context, False, {
            "type": "structured_rag_runtime",
            "version": "structured_rag_v1",
            "backend": "django_orm_keyword_search",
            "active_retrieval_backend": "structured_fallback",
            "external_vector_db": False,
            "retrieval_mode": "structured_only",
            "personalized_enabled": personalized_enabled,
            "personalized_hits": 0,
            "normalized_query": normalized_query,
            "query_expansions": query_expansions,
            "degraded": False,
            "query_intent": query_intent,
            "structured_enabled": structured_enabled,
        }

    if mode == "hybrid":
        docs = _merge_hybrid_documents(structured_docs, vector_docs, limit=limit)
        retrieval_runtime = build_retrieval_strategy(
            mode="hybrid",
            using_chroma=using_chroma,
            structured_hits=len(structured_docs),
            vector_hits=len(vector_docs),
            personalized_hits=len(personalized_docs),
            normalized_query=normalized_query,
            query_expansions=query_expansions,
        )
        retrieval_runtime["query_intent"] = query_intent
        retrieval_runtime["structured_enabled"] = structured_enabled
        if not using_chroma and structured_enabled and structured_docs:
            retrieval_runtime["backend"] = "structured_fallback"
            retrieval_runtime["active_retrieval_backend"] = "structured_fallback"
            retrieval_runtime["degraded_reason"] = "标准 Chroma 向量运行时不可用，当前优先使用结构化学习资料并由本地轻量向量补位。"
        return docs, structured_context, using_chroma, retrieval_runtime

    retrieval_runtime = build_retrieval_strategy(
        mode="vector_only",
        using_chroma=using_chroma,
        structured_hits=len(structured_docs),
        vector_hits=len(vector_docs),
        personalized_hits=len(personalized_docs),
        normalized_query=normalized_query,
        query_expansions=query_expansions,
    )
    retrieval_runtime["query_intent"] = query_intent
    retrieval_runtime["structured_enabled"] = structured_enabled
    retrieval_runtime["backend"] = backend_name or retrieval_runtime.get("backend") or "in_process_counter_cosine"
    retrieval_runtime["active_retrieval_backend"] = retrieval_runtime["backend"]
    return vector_docs, structured_context, using_chroma, retrieval_runtime


def run_vector_rag_search(query, limit=8, retrieval_mode="hybrid", user=None):
    query_bundle = normalize_learning_query(query)
    normalized_query = str(query_bundle.get("normalized_query") or query or "").strip()
    keywords = extract_query_keywords(normalized_query)
    docs, structured_context, using_chroma, retrieval_runtime = _rank_vector_documents(
        normalized_query,
        limit=limit,
        retrieval_mode=retrieval_mode,
        user=user,
    )
    docs = rerank_documents(normalized_query, _enrich_documents_with_highlights(docs, keywords), keywords, limit=limit)
    source_catalog = retrieval_runtime.get("knowledge_source_catalog") or []
    source_labels = " / ".join(item.get("label", item.get("key", "")) for item in source_catalog[:4])
    personalized_hits = int(retrieval_runtime.get("personalized_hits", 0) or 0)
    personalized_enabled = bool(retrieval_runtime.get("personalized_enabled"))
    personalized_note = f"，其中 {personalized_hits} 条来自你的个性知识库" if personalized_hits else ""
    query_intent = retrieval_runtime.get("query_intent") or classify_query_intent(normalized_query)
    is_learning_query = query_intent.get("intent") == "learning"
    content_label = "学习资料" if is_learning_query else "项目资料"

    if using_chroma:
        summary = f"已从项目知识库中检索到 {len(docs)} 条相关{content_label}。知识来源包括：{source_labels}{personalized_note}。"
    elif retrieval_runtime.get("backend") == "structured_fallback":
        summary = f"标准向量库暂不可用，已优先从结构化{content_label}里找到 {len(docs)} 条结果，并用本地轻量检索补位{personalized_note}。"
    elif retrieval_runtime.get("retrieval_mode") == "hybrid":
        summary = f"已完成 hybrid 检索，共找到 {len(docs)} 条{content_label}，其中 {personalized_hits} 条来自你的个性知识库。"
    else:
        summary = f"已用本地轻量向量检索到 {len(docs)} 条{content_label}，其中 {personalized_hits} 条来自你的个性知识库。"

    answer = {
        "summary": summary,
        "grounded_points": [
            f"{item['source_type']}：{item['title']}（相似度 {item['score']}）"
            for item in docs[:4]
        ],
        "next_questions": (
            ["生成专项练习", "解释第一条结果", "换一种更简单的说法"]
            if is_learning_query
            else ["给我对应接口", "告诉我相关页面入口", "整理成执行步骤"]
        ),
    }
    if is_provider_ready():
        system_prompt = (
            "You are a grounded English-learning RAG tutor. "
            "Use only the provided retrieved knowledge chunks and return strict JSON only."
            if is_learning_query
            else "You are a grounded assistant for the GAClearn project. "
            "Use only the provided retrieved project knowledge chunks and return strict JSON only."
        )
        payload = {
            "query": query,
            "local_vector_docs": docs,
            "task": (
                "Answer the learner's English study question using only the retrieved project knowledge chunks. Return strict JSON only."
                if is_learning_query
                else "Answer the user's project/product question using only the retrieved project knowledge chunks. Return strict JSON only."
            ),
            "output_schema": {
                "summary": "string",
                "grounded_points": ["string"],
                "next_questions": ["string"],
            },
        }
        try:
            ai_result = chat_json(
                [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
                ],
                temperature=0.2,
            )
            answer.update({key: ai_result.get(key) or answer[key] for key in answer})
        except Exception as exc:
            answer["provider_error"] = str(exc)

    answer_points = [item for item in (answer.get("grounded_points") or []) if item][:4]
    source_pills = []
    for item in docs[:6]:
        label = item.get("title") or item.get("source_type") or ""
        if label:
            source_pills.append(
                {
                    "label": label[:28],
                    "source_type": item.get("source_type", ""),
                    "audience": str(((item.get("metadata") or {}).get("audience")) or ""),
                }
            )
    seen_pills = []
    deduped_pills = []
    for item in source_pills:
        key = f"{item.get('label')}:{item.get('source_type')}"
        if key in seen_pills:
            continue
        seen_pills.append(key)
        deduped_pills.append(item)
    answer_brief = {
        "summary": answer.get("summary", ""),
        "points": answer_points[:4],
        "next_questions": (answer.get("next_questions") or [])[:3],
    }
    advanced_debug = {
        "query_intent": query_intent,
        "retrieval_strategy": retrieval_runtime,
        "documents_preview_count": len(docs),
        "using_chroma": using_chroma,
        "structured_context_available": bool(structured_context),
    }

    degraded_reason = str(retrieval_runtime.get("degraded_reason") or "").strip()
    degraded_notice = None
    if retrieval_runtime.get("degraded"):
        degraded_notice = {
            "enabled": True,
            "reason": degraded_reason or "标准向量运行时不可用。",
            "message": degraded_reason or "标准向量运行时不可用，当前结果已自动降级。",
        }

    payload = {
        "query": query,
        "answer": answer,
        "answer_brief": answer_brief,
        "source_pills": deduped_pills[:6],
        "advanced_debug": advanced_debug,
        "documents": docs,
        "retrieval_explain": {
            "mode": retrieval_runtime.get("retrieval_mode", retrieval_mode),
            "keywords": keywords,
            "normalized_query": normalized_query,
            "query_expansions": query_bundle.get("query_expansions") or [],
            "using_chroma": using_chroma,
            "using_hybrid": retrieval_runtime.get("retrieval_mode") == "hybrid",
            "structured_context_available": bool(structured_context),
            "personalized_enabled": personalized_enabled,
            "personalized_hits": personalized_hits,
            "rerank_enabled": True,
            "multi_route_enabled": True,
            "query_intent": query_intent,
            "why_this_result": [
                "优先保留命中更多关键词的资料。",
                "如果同一条资料同时被结构化检索和向量召回命中，会排得更靠前。",
                "每条结果都附带 matched_keywords、highlights、match_reason 和 rerank_score，便于解释原因。",
                "如果你主动开启并构建了个性化 RAG，系统会把学习计划、错词本、最近行为和语法薄弱点一起纳入召回。",
            ],
        },
        "structured_context": structured_context or {},
        "retrieval_strategy": retrieval_runtime,
        "ai_strategy": _provider_meta(),
    }
    if degraded_notice:
        payload["degraded_notice"] = degraded_notice
    return payload


def _build_rag_answer(query, context):
    if not is_provider_ready():
        first_point = context.get("grammar_points", [{}])[0]
        first_word = context.get("words", [{}])[0]
        return {
            "summary": f"已从项目词库和语法库里检索到与“{query}”相关的内容。",
            "grounded_points": [
                f"相关语法：{first_point.get('title', '暂无匹配语法点')}",
                f"相关词汇：{first_word.get('word', '暂无匹配词汇')}",
            ],
            "next_questions": ["再给我一个例句", "用这个点出一道练习", "关联哪些易混词"],
        }
    payload = {
        "query": query,
        "retrieved_context": context,
        "task": "Answer the user's English learning query using only retrieved context. Return strict JSON only.",
        "output_schema": {
            "summary": "string",
            "grounded_points": ["string"],
            "next_questions": ["string"],
        },
    }
    try:
        return chat_json(
            [
                {"role": "system", "content": "You are a grounded RAG tutor. Use only provided context and return strict JSON."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        fallback = {
            "summary": f"已从项目词库和语法库里检索到与“{query}”相关的内容。",
            "grounded_points": [
                f"相关语法：{context.get('grammar_points', [{}])[0].get('title', '暂无匹配语法点')}",
                f"相关词汇：{context.get('words', [{}])[0].get('word', '暂无匹配词汇')}",
            ],
            "next_questions": ["再给我一个例句", "用这个点出一道练习", "关联哪些易混词"],
            "provider_error": str(exc),
        }
        return fallback


def build_multi_agent_brief(user):
    bundle = build_study_coach_bundle(user, trend_days=7)
    return {
        "headline": "多 Agent 协作架构说明",
        "agents": [
            {
                "name": "supervisor",
                "focus": "统一接收 planner / retriever / coach 的结果，并决定最终输出。",
                "action": "负责汇总最终学习计划或最终检索答案。",
            },
            {
                "name": "planner",
                "focus": "先定义这次任务的焦点，是保守复习、平衡推进，还是做规则解释。",
                "action": "负责问题分析、任务优先级和初始策略。",
            },
            {
                "name": "retriever",
                "focus": "调用计划、错词、RAG、快照与长期记忆来补证据。",
                "action": "负责 structured / vector / hybrid 等检索与证据比较。",
            },
            {
                "name": "coach",
                "focus": "把系统策略翻译成学习者能直接看懂、直接执行的建议。",
                "action": "负责可读解释、下一步动作与提醒。",
            },
        ],
        "recommended_flow": ["planner -> retriever -> coach -> supervisor", "学习计划链路和检索问答链路都复用这套角色分工"],
        "demos": [
            {"name": "学习计划重规划", "entry": "/api/v1/ai/plans/replan", "status": "active"},
            {"name": "检索问答编排", "entry": "/api/v1/ai/agents/retrieval-orchestrator", "status": "active"},
        ],
        "snapshot": bundle,
        "ai_strategy": _provider_meta(),
    }


def summarize_ai_quality(user):
    from django.utils import timezone

    from .models import AIMessage, AIRequestLog, AIResponseCache, AIUserFeedback

    feedback_counter = Counter(AIUserFeedback.objects.filter(user=user).values_list("rating", flat=True))
    message_count = AIMessage.objects.filter(conversation__user=user).count()
    recent_logs = AIRequestLog.objects.filter(user=user, created_at__gte=timezone.now() - timedelta(days=7))
    status_counter = Counter(recent_logs.values_list("status", flat=True))
    cache_hits = recent_logs.filter(cache_hit=True).count()
    request_count = recent_logs.count()
    return {
        "message_count": message_count,
        "week_request_count": request_count,
        "cache_hit_count": cache_hits,
        "active_cache_items": AIResponseCache.objects.filter(expires_at__gt=timezone.now()).count(),
        "feedback_summary": dict(feedback_counter),
        "status_summary": dict(status_counter),
        "quality_notes": [
            "当前已记录 AI 会话和用户反馈，可用于后续人工抽检。",
            "当前已接入 AI 运行日志、响应缓存、基础限流和缓存命中统计。",
        ],
        "ai_strategy": _provider_meta(),
    }
