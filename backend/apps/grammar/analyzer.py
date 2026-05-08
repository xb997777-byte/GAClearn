import re

from apps.books.models import Word

from .ai import enrich_sentence_analysis
from .services import COLOR_PALETTE, DIFFICULTY_LABELS, ROLE_LABELS, build_legend


TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+|[^\w\s]")

ARTICLES = {"a", "an", "the"}
DETERMINERS = ARTICLES | {
    "this",
    "that",
    "these",
    "those",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "some",
    "any",
    "each",
    "every",
    "many",
    "much",
    "few",
    "several",
    "all",
    "both",
    "another",
}
BE_VERBS = {"am", "is", "are", "was", "were", "be", "been", "being"}
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}
DO_VERBS = {"do", "does", "did"}
HAVE_VERBS = {"have", "has", "had"}
AUXILIARIES = BE_VERBS | MODALS | DO_VERBS | HAVE_VERBS
LINKING_VERBS = BE_VERBS | {"seem", "become", "feel", "look", "sound", "smell", "taste", "remain", "stay", "grow", "turn", "appear", "get"}
RELATIVE_PRONOUNS = {"who", "whom", "whose", "which", "that", "where", "when"}
CLAUSE_MARKERS = {
    "if",
    "when",
    "because",
    "although",
    "while",
    "since",
    "unless",
    "after",
    "before",
    "once",
    "until",
    "though",
    "whereas",
    "whether",
    "that",
    "what",
    "how",
    "why",
}
PREPOSITIONS = {
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "from",
    "of",
    "by",
    "about",
    "over",
    "under",
    "through",
    "during",
    "before",
    "after",
    "into",
    "around",
    "between",
    "among",
    "against",
    "without",
    "within",
    "behind",
    "beside",
    "near",
    "across",
    "toward",
    "towards",
    "past",
    "like",
    "than",
    "as",
}
INTERNAL_PREPOSITIONS = {"of"}
MID_ADVERBS = {"always", "usually", "often", "sometimes", "never", "already", "still", "just", "really"}
TIME_ADVERBS = {"today", "yesterday", "tomorrow", "now", "tonight", "soon", "later", "recently", "daily", "weekly"}
CONJUNCTIONS = {"and", "but", "or", "so", "yet", "nor"}
COMMON_VERBS = {
    "accept",
    "add",
    "analyze",
    "answer",
    "appear",
    "arrive",
    "ask",
    "become",
    "begin",
    "believe",
    "bring",
    "build",
    "call",
    "change",
    "check",
    "choose",
    "compare",
    "complete",
    "cover",
    "create",
    "decide",
    "describe",
    "discuss",
    "display",
    "do",
    "enjoy",
    "explain",
    "feel",
    "find",
    "finish",
    "follow",
    "give",
    "go",
    "grow",
    "have",
    "help",
    "hold",
    "improve",
    "include",
    "keep",
    "know",
    "learn",
    "leave",
    "listen",
    "look",
    "make",
    "mean",
    "move",
    "need",
    "offer",
    "open",
    "pass",
    "plan",
    "practice",
    "prepare",
    "prove",
    "read",
    "remember",
    "remain",
    "review",
    "say",
    "seem",
    "share",
    "show",
    "sound",
    "speak",
    "start",
    "stay",
    "study",
    "support",
    "take",
    "tell",
    "think",
    "try",
    "turn",
    "understand",
    "update",
    "use",
    "want",
    "watch",
    "work",
    "write",
}
IRREGULAR_LEMMAS = {
    "am": "be",
    "is": "be",
    "are": "be",
    "was": "be",
    "were": "be",
    "been": "be",
    "being": "be",
    "does": "do",
    "did": "do",
    "done": "do",
    "has": "have",
    "had": "have",
    "goes": "go",
    "went": "go",
    "gone": "go",
    "comes": "come",
    "came": "come",
    "taken": "take",
    "took": "take",
    "made": "make",
    "gave": "give",
    "given": "give",
    "wrote": "write",
    "written": "write",
    "saw": "see",
    "seen": "see",
    "found": "find",
    "felt": "feel",
    "thought": "think",
    "told": "tell",
    "said": "say",
    "read": "read",
    "kept": "keep",
    "left": "leave",
    "began": "begin",
    "begun": "begin",
    "shown": "show",
    "grew": "grow",
    "grown": "grow",
    "became": "become",
    "studies": "study",
    "tries": "try",
    "uses": "use",
    "offers": "offer",
    "explains": "explain",
    "checks": "check",
    "starts": "start",
    "helps": "help",
    "makes": "make",
    "means": "mean",
}
FUNCTION_TRANSLATIONS = {
    "i": "我",
    "you": "你",
    "he": "他",
    "she": "她",
    "it": "它",
    "we": "我们",
    "they": "他们",
    "me": "我",
    "him": "他",
    "her": "她",
    "us": "我们",
    "them": "他们",
    "my": "我的",
    "your": "你的",
    "his": "他的",
    "our": "我们的",
    "their": "他们的",
    "this": "这",
    "that": "那",
    "these": "这些",
    "those": "那些",
    "a": "",
    "an": "",
    "the": "",
    "in": "在",
    "on": "在",
    "at": "在",
    "to": "去",
    "for": "为了",
    "with": "和",
    "from": "从",
    "of": "的",
    "by": "被",
    "about": "关于",
    "before": "在…之前",
    "after": "在…之后",
    "during": "在…期间",
    "into": "进入",
    "around": "在周围",
    "between": "在…之间",
    "through": "通过",
    "because": "因为",
    "if": "如果",
    "when": "当…时",
    "although": "虽然",
    "while": "当…时",
    "since": "因为",
    "unless": "除非",
    "that": "这",
    "what": "什么",
    "how": "如何",
    "why": "为什么",
    "who": "……的人",
    "which": "……的那个",
    "where": "……的地方",
    "than": "比",
    "as": "像",
    "and": "并且",
    "but": "但是",
    "or": "或者",
    "will": "将",
    "would": "会",
    "can": "能",
    "could": "能够",
    "should": "应该",
    "may": "可以",
    "might": "也许",
    "must": "必须",
    "have": "已经",
    "has": "已经",
    "had": "已经",
    "do": "做",
    "does": "做",
    "did": "做了",
    "am": "是",
    "is": "是",
    "are": "是",
    "was": "是",
    "were": "是",
    "be": "是",
    "been": "已经",
    "being": "正在",
    "not": "不",
    "very": "非常",
    "today": "今天",
    "yesterday": "昨天",
    "tomorrow": "明天",
    "now": "现在",
    "always": "总是",
    "usually": "通常",
    "often": "经常",
    "sometimes": "有时",
    "never": "从不",
    "already": "已经",
    "still": "仍然",
    "just": "刚刚",
    "really": "真的",
}
FIXED_EXPRESSION_TRANSLATIONS = {
    "thank you": "谢谢你",
    "thank you very much": "非常感谢你",
    "thanks": "谢谢",
    "thanks a lot": "非常感谢",
    "you are welcome": "不客气",
    "you're welcome": "不客气",
    "excuse me": "打扰一下",
    "i am sorry": "对不起",
    "i'm sorry": "对不起",
    "never mind": "没关系",
    "see you": "再见",
    "good morning": "早上好",
    "good afternoon": "下午好",
    "good evening": "晚上好",
    "good night": "晚安",
    "how are you": "你好吗",
}
WORD_TRANSLATION_OVERRIDES = {
    "teacher": "老师",
    "student": "学生",
    "students": "学生",
    "essay": "作文",
    "essays": "作文",
    "class": "课堂",
    "meeting": "会议",
    "grammar": "语法",
    "rule": "规则",
    "advice": "建议",
    "lesson": "课程",
    "plan": "计划",
    "review": "复习",
    "practice": "练习",
    "homework": "作业",
    "book": "书",
    "books": "书",
    "answer": "答案",
    "answers": "答案",
    "note": "笔记",
    "notes": "笔记",
    "help": "帮助",
    "helps": "帮助",
    "offer": "提供",
    "offers": "提供",
    "explain": "解释",
    "explains": "解释",
    "check": "检查",
    "checks": "检查",
    "start": "开始",
    "starts": "开始",
    "learn": "学习",
    "study": "学习",
    "studies": "学习",
    "improve": "提升",
    "share": "分享",
    "prepare": "准备",
    "prepared": "准备好的",
    "use": "使用",
    "used": "使用",
    "clear": "清晰的",
    "new": "新的",
    "happy": "开心的",
    "every": "每",
    "week": "周",
    "daily": "每天",
}
ROLE_EXPLANATIONS = {
    "subject": "{text} 是句子的主语，说明谁在做动作，或者句子主要围绕谁展开。",
    "predicate": "{text} 是句子的谓语核心，承担主要动作、状态和时态信息。",
    "object": "{text} 是宾语，表示动作作用到谁或什么。",
    "complement": "{text} 是补语或表语，用来补充主语的状态、身份或结果。",
    "adverbial": "{text} 是状语，补充时间、地点、方式、程度等背景信息。",
    "modifier": "{text} 是修饰成分，用来进一步限定前后的核心信息。",
    "clause": "{text} 是从句部分，阅读时建议先抓主干，再把它作为补充信息回填进去。",
    "infinitive": "{text} 是不定式结构，常用来表达目的、计划或补充说明。",
    "gerund": "{text} 是动名词结构，在句中整体承担一个成分。",
    "comparison": "{text} 是比较结构，用来体现对象之间的差异或程度对比。",
    "connector": "{text} 起连接作用，把前后两部分衔接起来。",
}


def analyze_sentence_input(sentence_text, enable_ai_enrichment=True):
    sentence = _normalize_sentence(sentence_text)
    tokens = _tokenize_sentence(sentence)
    words = [token for token in tokens if token["is_word"]]
    if not words:
        raise ValueError("sentence is empty")

    lexicon = _load_lexicon(words)
    normalized_sentence = _normalize_phrase_text(words, 0, len(words) - 1)
    if normalized_sentence in FIXED_EXPRESSION_TRANSLATIONS:
        phrase_specs = [
            {
                "start": 0,
                "end": len(words) - 1,
                "role_type": "plain",
                "grammar_label": "固定表达",
                "is_core": True,
            }
        ]
    else:
        phrase_specs = _infer_phrases(tokens, words, lexicon)
    annotations = _build_annotations(sentence, words, phrase_specs)
    chunk_breakdown = _build_chunk_breakdown(words, phrase_specs, lexicon)
    main_structure = _build_main_structure(chunk_breakdown)
    grammar_tags = _build_grammar_tags(sentence, words, chunk_breakdown)
    difficulty = _infer_difficulty(words, chunk_breakdown)
    structure_label = _infer_structure_label(chunk_breakdown)
    tense_label = _infer_tense_label(words, chunk_breakdown)
    summary = _build_summary(structure_label, tense_label, chunk_breakdown)
    analysis = _build_analysis(main_structure, chunk_breakdown)
    translation_cn = _build_translation(chunk_breakdown)

    result = {
        "id": 0,
        "source_type": "custom",
        "sentence": sentence,
        "translation_cn": translation_cn,
        "summary": summary,
        "analysis": analysis,
        "main_structure": main_structure,
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_LABELS.get(difficulty, "基础"),
        "scene_tag": "自由输入",
        "grammar_tags": grammar_tags,
        "is_long_sentence": len(words) >= 16 or sum(1 for item in chunk_breakdown if not item["is_core"]) >= 2,
        "point": {
            "id": 0,
            "title": "即时拆句",
            "code": "custom-analyze",
            "category": "自定义分析",
        },
        "progress": {
            "last_action": "",
            "mastery_level": 0,
            "practice_total": 0,
            "correct_total": 0,
            "is_bookmarked": False,
            "occurred_at": None,
        },
        "legend": build_legend(),
        "annotations": annotations,
        "complete_segments": _build_segments_from_annotations(sentence, annotations, core_only=False),
        "core_segments": _build_segments_from_annotations(sentence, annotations, core_only=True),
        "chunk_breakdown": chunk_breakdown,
        "practice": {
            "type": "choice",
            "prompt": "",
            "options": [],
            "answer": "",
            "explanation": "",
        },
        "point_detail": {
            "id": 0,
            "title": "即时拆句",
            "category": "自定义分析",
            "description": "根据你输入的英文句子即时生成语法拆解结果。",
            "learning_tip": _build_learning_tip(chunk_breakdown),
            "difficulty": difficulty,
            "difficulty_label": DIFFICULTY_LABELS.get(difficulty, "基础"),
        },
        "navigation": {
            "previous_sentence_id": None,
            "next_sentence_id": None,
        },
    }
    result["analysis_mode"] = "rule"
    if not enable_ai_enrichment:
        return result

    try:
        return enrich_sentence_analysis(sentence, result)
    except Exception:
        return result


def _normalize_sentence(sentence_text):
    sentence = re.sub(r"\s+", " ", (sentence_text or "").strip())
    if not sentence:
        return ""
    if sentence[-1] not in ".!?":
        sentence = f"{sentence}."
    return sentence


def _tokenize_sentence(sentence):
    result = []
    for match in TOKEN_PATTERN.finditer(sentence):
        text = match.group(0)
        result.append(
            {
                "text": text,
                "lower": text.lower(),
                "start": match.start(),
                "end": match.end(),
                "is_word": bool(re.match(r"[A-Za-z0-9]", text)),
            }
        )
    for index, item in enumerate(result):
        item["full_index"] = index
    return result


def _candidate_forms(word):
    lower = word.lower()
    forms = [lower]

    lemma = IRREGULAR_LEMMAS.get(lower)
    if lemma and lemma not in forms:
        forms.append(lemma)

    if lower.endswith("ies") and len(lower) > 3:
        forms.append(lower[:-3] + "y")
    if lower.endswith("es") and len(lower) > 2:
        forms.append(lower[:-2])
    if lower.endswith("s") and len(lower) > 1:
        forms.append(lower[:-1])
    if lower.endswith("ing") and len(lower) > 4:
        forms.append(lower[:-3])
        forms.append(lower[:-3] + "e")
    if lower.endswith("ed") and len(lower) > 3:
        forms.append(lower[:-2])
        forms.append(lower[:-1])
        forms.append(lower[:-2] + "e")

    unique = []
    for item in forms:
        if item and item not in unique:
            unique.append(item)
    return unique


def _load_lexicon(words):
    lookup_terms = set()
    for item in words:
        lookup_terms.update(_candidate_forms(item["lower"]))

    rows = Word.objects.filter(word__in=list(lookup_terms)).values("word", "meaning_cn", "part_of_speech")
    lexicon = {}
    for row in rows:
        key = row["word"].lower()
        if key not in lexicon:
            lexicon[key] = row
    return lexicon


def _lookup_entry(word, lexicon):
    for candidate in _candidate_forms(word):
        if candidate in lexicon:
            return lexicon[candidate]
    return None


def _extract_meaning(meaning_cn):
    text = (meaning_cn or "").strip()
    if not text:
        return ""
    text = re.split(r"[；;，,/（(]", text)[0].strip()
    return text


def _is_separator_between(tokens, left_word, right_word):
    for token in tokens[left_word["full_index"] + 1 : right_word["full_index"]]:
        if token["text"] in {",", ";", ":"}:
            return True
    return False


def _is_likely_verb(words, index, lexicon):
    lower = words[index]["lower"]
    prev_lower = words[index - 1]["lower"] if index > 0 else ""
    next_lower = words[index + 1]["lower"] if index + 1 < len(words) else ""

    if lower in AUXILIARIES or lower in COMMON_VERBS or lower in LINKING_VERBS:
        return True

    entry = _lookup_entry(lower, lexicon)
    pos = (entry.get("part_of_speech") if entry else "") or ""
    if pos.startswith("v."):
        return True

    if lower.endswith("ing") and prev_lower not in DETERMINERS:
        return True

    if lower.endswith("ed") or lower.endswith("en"):
        return True

    if lower.endswith("s") and prev_lower not in DETERMINERS and prev_lower not in PREPOSITIONS:
        if next_lower not in CONJUNCTIONS:
            return True

    return False


def _find_first_comma_word_index(tokens, words):
    comma_full_index = next((item["full_index"] for item in tokens if item["text"] == ","), None)
    if comma_full_index is None:
        return None
    candidate = None
    for index, item in enumerate(words):
        if item["full_index"] < comma_full_index:
            candidate = index
        else:
            break
    return candidate


def _find_predicate_anchor(words, lexicon, start_index):
    candidate_indices = [index for index in range(start_index, len(words)) if _is_likely_verb(words, index, lexicon)]
    if not candidate_indices:
        return None

    has_relative_clause = any(words[index]["lower"] in RELATIVE_PRONOUNS for index in range(start_index, candidate_indices[-1] + 1))
    if start_index < len(words) and words[start_index]["lower"] in CLAUSE_MARKERS:
        return candidate_indices[-1]
    if has_relative_clause:
        return candidate_indices[-1]
    return candidate_indices[0]


def _expand_predicate_left(words, anchor_index, start_index):
    predicate_start = anchor_index
    while predicate_start - 1 >= start_index:
        prev_lower = words[predicate_start - 1]["lower"]
        if prev_lower in AUXILIARIES or prev_lower in {"not"}:
            predicate_start -= 1
            continue
        if prev_lower in MID_ADVERBS and predicate_start - 2 >= start_index and words[predicate_start - 2]["lower"] in AUXILIARIES:
            predicate_start -= 1
            continue
        break
    return predicate_start


def _expand_predicate_right(words, predicate_start, lexicon):
    predicate_end = predicate_start
    start_lower = words[predicate_start]["lower"]

    while predicate_end + 1 < len(words):
        next_lower = words[predicate_end + 1]["lower"]
        current_lower = words[predicate_end]["lower"]

        if next_lower in MID_ADVERBS and predicate_end + 2 < len(words) and _is_likely_verb(words, predicate_end + 2, lexicon):
            predicate_end += 1
            continue

        if current_lower in MODALS and _is_likely_verb(words, predicate_end + 1, lexicon):
            predicate_end += 1
            continue

        if current_lower in HAVE_VERBS and (next_lower.endswith("ed") or next_lower.endswith("en") or next_lower in BE_VERBS):
            predicate_end += 1
            continue

        if current_lower in BE_VERBS:
            if next_lower in BE_VERBS:
                predicate_end += 1
                continue
            if next_lower.endswith("ing"):
                predicate_end += 1
                continue
            if (next_lower.endswith("ed") or next_lower.endswith("en")) and any(item["lower"] == "by" for item in words[predicate_end + 1 :]):
                predicate_end += 1
                continue

        if current_lower in DO_VERBS and _is_likely_verb(words, predicate_end + 1, lexicon):
            predicate_end += 1
            continue

        if start_lower not in AUXILIARIES and predicate_end == predicate_start:
            break

        break

    return predicate_end


def _consume_phrase(words, tokens, start_index, stop_words=None):
    stop_words = stop_words or set()
    end_index = start_index

    for index in range(start_index + 1, len(words)):
        lower = words[index]["lower"]
        if _is_separator_between(tokens, words[index - 1], words[index]):
            break
        if lower in stop_words:
            break
        if lower in PREPOSITIONS and lower not in INTERNAL_PREPOSITIONS and words[start_index]["lower"] not in PREPOSITIONS:
            break
        if lower in CLAUSE_MARKERS and words[start_index]["lower"] not in CLAUSE_MARKERS:
            break
        if lower in TIME_ADVERBS and words[start_index]["lower"] not in TIME_ADVERBS:
            break
        end_index = index

    return end_index


def _infer_clause_label(start_word):
    lower = start_word["lower"]
    if lower in RELATIVE_PRONOUNS:
        return "定语从句"
    if lower in {"that", "whether", "what", "how", "why"}:
        return "宾语从句"
    return "状语从句"


def _looks_like_clause_start(words, start_index, lexicon):
    lower = words[start_index]["lower"]
    if lower not in CLAUSE_MARKERS:
        return False
    if lower not in {"before", "after", "since", "while", "as"}:
        return True
    search_end = min(len(words), start_index + 5)
    return any(_is_likely_verb(words, index, lexicon) for index in range(start_index + 1, search_end))


def _infer_structure_label(chunk_breakdown):
    has_complement = any(item["role_type"] == "complement" for item in chunk_breakdown)
    has_object = any(item["role_type"] == "object" for item in chunk_breakdown)
    if has_complement:
        return "主系表/补语结构"
    if has_object:
        return "主谓宾结构"
    return "主谓结构"


def _infer_tense_label(words, chunk_breakdown):
    predicate = next((item for item in chunk_breakdown if item["role_type"] == "predicate"), None)
    if not predicate:
        return "基础句式"

    text = predicate["en"].lower()
    if "will " in text or text.startswith("will"):
        return "一般将来时"
    if any(word in text.split() for word in {"am", "is", "are"}) and any(part.endswith("ing") for part in text.split()):
        return "现在进行时"
    if any(word in text.split() for word in {"was", "were"}) and any(part.endswith("ing") for part in text.split()):
        return "过去进行时"
    if any(word in text.split() for word in {"have", "has", "had"}) and any(part.endswith("ed") or part.endswith("en") for part in text.split()):
        return "完成时"
    if any(word in text.split() for word in {"was", "were", "did", "had"}) or any(part.endswith("ed") for part in text.split()):
        return "一般过去时"
    return "一般现在时"


def _infer_difficulty(words, chunk_breakdown):
    clause_count = sum(1 for item in chunk_breakdown if item["role_type"] == "clause")
    if clause_count or len(words) >= 16:
        return 3 if len(words) >= 18 or clause_count >= 2 else 2
    if len(words) >= 10 or any(item["role_type"] == "adverbial" for item in chunk_breakdown):
        return 2
    return 1


def _infer_phrases(tokens, words, lexicon):
    phrases = []
    main_start = 0

    if words and _looks_like_clause_start(words, 0, lexicon):
        comma_word_index = _find_first_comma_word_index(tokens, words)
        if comma_word_index is not None and comma_word_index >= 0:
            phrases.append({"start": 0, "end": comma_word_index, "role_type": "clause", "grammar_label": _infer_clause_label(words[0]), "is_core": False})
            main_start = comma_word_index + 1

    if main_start == 0 and len(words) > 1 and words[0]["lower"] in MID_ADVERBS | TIME_ADVERBS:
        phrases.append({"start": 0, "end": 0, "role_type": "adverbial", "grammar_label": "状语", "is_core": False})
        main_start = 1

    if main_start == 0 and words and words[0]["lower"] in PREPOSITIONS:
        comma_word_index = _find_first_comma_word_index(tokens, words)
        if comma_word_index is not None and comma_word_index >= 0:
            phrases.append({"start": 0, "end": comma_word_index, "role_type": "adverbial", "grammar_label": "状语", "is_core": False})
            main_start = comma_word_index + 1

    predicate_anchor = _find_predicate_anchor(words, lexicon, main_start)
    if predicate_anchor is None:
        phrases.append({"start": main_start, "end": len(words) - 1, "role_type": "subject", "grammar_label": "主语", "is_core": True})
        return phrases

    predicate_start = _expand_predicate_left(words, predicate_anchor, main_start)
    predicate_end = _expand_predicate_right(words, predicate_start, lexicon)

    subject_start = main_start
    subject_end = predicate_start - 1

    trailing_adverb_start = None
    while subject_end >= subject_start and words[subject_end]["lower"] in MID_ADVERBS:
        trailing_adverb_start = subject_end
        subject_end -= 1

    if subject_start <= subject_end:
        relative_index = next((index for index in range(subject_start + 1, subject_end + 1) if words[index]["lower"] in RELATIVE_PRONOUNS), None)
        if relative_index is not None:
            if subject_start <= relative_index - 1:
                phrases.append({"start": subject_start, "end": relative_index - 1, "role_type": "subject", "grammar_label": "主语", "is_core": True})
            phrases.append({"start": relative_index, "end": subject_end, "role_type": "clause", "grammar_label": "定语从句", "is_core": False})
        else:
            role_type = "subject"
            grammar_label = "主语"
            if words[subject_start]["lower"].endswith("ing") and words[subject_start]["lower"] not in AUXILIARIES:
                role_type = "gerund"
                grammar_label = "动名词主语"
            elif words[subject_start]["lower"] == "to" and subject_start < subject_end:
                role_type = "infinitive"
                grammar_label = "不定式主语"
            phrases.append({"start": subject_start, "end": subject_end, "role_type": role_type, "grammar_label": grammar_label, "is_core": True})

    if trailing_adverb_start is not None:
        phrases.append({"start": trailing_adverb_start, "end": predicate_start - 1, "role_type": "adverbial", "grammar_label": "状语", "is_core": False})

    phrases.append({"start": predicate_start, "end": predicate_end, "role_type": "predicate", "grammar_label": "谓语", "is_core": True})

    cursor = predicate_end + 1
    while cursor < len(words):
        role_type, grammar_label = _infer_tail_role(words, cursor, phrases, lexicon)
        phrase_end = _consume_phrase(words, tokens, cursor, stop_words=PREPOSITIONS | CLAUSE_MARKERS | TIME_ADVERBS)

        if role_type == "adverbial" and words[cursor]["lower"] in PREPOSITIONS:
            phrase_end = _consume_phrase(words, tokens, cursor, stop_words=CLAUSE_MARKERS | TIME_ADVERBS)

        if role_type == "clause":
            phrase_end = len(words) - 1
        elif role_type == "comparison":
            phrase_end = _consume_phrase(words, tokens, cursor, stop_words=CLAUSE_MARKERS | TIME_ADVERBS)

        phrases.append({"start": cursor, "end": phrase_end, "role_type": role_type, "grammar_label": grammar_label, "is_core": role_type in {"object", "complement"}})
        cursor = phrase_end + 1

    phrases.sort(key=lambda item: (words[item["start"]]["start"], words[item["end"]]["end"]))
    return phrases


def _infer_tail_role(words, cursor, phrases, lexicon):
    lower = words[cursor]["lower"]
    predicate_phrase = next((item for item in phrases if item["role_type"] == "predicate"), None)
    predicate_text = ""
    if predicate_phrase:
        predicate_text = " ".join(word["lower"] for word in words[predicate_phrase["start"] : predicate_phrase["end"] + 1])

    if _looks_like_clause_start(words, cursor, lexicon):
        return "clause", _infer_clause_label(words[cursor])
    if lower == "to" and cursor + 1 < len(words):
        return "infinitive", "不定式"
    if lower.endswith("ing") and lower not in AUXILIARIES:
        return "gerund", "动名词结构"
    if lower in PREPOSITIONS or lower in TIME_ADVERBS or lower.endswith("ly"):
        return "adverbial", "状语"
    if " than " in f" {' '.join(word['lower'] for word in words[cursor:])} ":
        return "comparison", "比较结构"
    if any(item in predicate_text.split() for item in LINKING_VERBS):
        return "complement", "补语/表语"
    return "object", "宾语"


def _build_annotations(sentence, words, phrase_specs):
    annotations = []
    for index, item in enumerate(phrase_specs, start=1):
        start_word = words[item["start"]]
        end_word = words[item["end"]]
        role_type = item["role_type"]
        text = sentence[start_word["start"] : end_word["end"]]
        palette = COLOR_PALETTE.get(role_type, COLOR_PALETTE["plain"])
        grammar_label = item.get("grammar_label") or ROLE_LABELS.get(role_type, role_type)
        explanation = ROLE_EXPLANATIONS.get(role_type, "{text} 是句子中的一个成分。").format(text=text)
        role_label = ROLE_LABELS.get(role_type, role_type)
        if grammar_label == "固定表达":
            role_label = "固定表达"
            explanation = f"{text} 是固定表达，理解时优先整体把握它的常见使用场景。"
        annotations.append(
            {
                "id": index,
                "text_span": text,
                "start_index": start_word["start"],
                "end_index": end_word["end"],
                "role_type": role_type,
                "role_label": role_label,
                "grammar_label": grammar_label,
                "explanation": explanation,
                "color_token": role_type,
                "background": palette["bg"],
                "color": palette["color"],
                "is_core": bool(item.get("is_core")),
            }
        )
    return annotations


def _normalize_phrase_text(words, start_index, end_index):
    return " ".join(item["lower"] for item in words[start_index : end_index + 1]).strip()


def _lookup_fixed_expression_translation(words, start_index, end_index):
    phrase = _normalize_phrase_text(words, start_index, end_index)
    return FIXED_EXPRESSION_TRANSLATIONS.get(phrase, "")


def _translate_phrase(words, start_index, end_index, lexicon):
    fixed_translation = _lookup_fixed_expression_translation(words, start_index, end_index)
    if fixed_translation:
        return fixed_translation

    first_lower = words[start_index]["lower"]
    if first_lower in {"in", "on", "at"} and start_index < end_index:
        inner = _translate_phrase(words, start_index + 1, end_index, lexicon)
        return f"在{inner}" if inner else "在"
    if first_lower == "before" and start_index < end_index:
        inner = _translate_phrase(words, start_index + 1, end_index, lexicon)
        return f"在{inner}之前" if inner else "之前"
    if first_lower == "after" and start_index < end_index:
        inner = _translate_phrase(words, start_index + 1, end_index, lexicon)
        return f"在{inner}之后" if inner else "之后"
    if first_lower == "during" and start_index < end_index:
        inner = _translate_phrase(words, start_index + 1, end_index, lexicon)
        return f"在{inner}期间" if inner else "期间"

    parts = []
    for item in words[start_index : end_index + 1]:
        lower = item["lower"]
        if lower in ARTICLES:
            continue
        if lower in WORD_TRANSLATION_OVERRIDES:
            translated = WORD_TRANSLATION_OVERRIDES[lower]
        elif lower in FUNCTION_TRANSLATIONS:
            translated = FUNCTION_TRANSLATIONS[lower]
        else:
            entry = _lookup_entry(lower, lexicon)
            translated = _extract_meaning(entry["meaning_cn"]) if entry else item["text"]
        if translated:
            parts.append(translated)
    return "".join(parts) if parts else "".join(item["text"] for item in words[start_index : end_index + 1])


def _build_chunk_breakdown(words, phrase_specs, lexicon):
    result = []
    for item in phrase_specs:
        text = " ".join(word["text"] for word in words[item["start"] : item["end"] + 1])
        role_type = item["role_type"]
        role_label = item.get("grammar_label") or ROLE_LABELS.get(role_type, role_type)
        note = ROLE_EXPLANATIONS.get(role_type, "{text} 是句子中的一个成分。").format(text=text)
        if role_label == "固定表达":
            note = f"{text} 是固定表达，适合整体记忆，不建议逐词硬译。"
        result.append(
            {
                "en": text,
                "cn": _translate_phrase(words, item["start"], item["end"], lexicon),
                "role_label": role_label,
                "note": note,
                "is_core": bool(item.get("is_core")),
                "role_type": role_type,
            }
        )
    return result


def _build_main_structure(chunk_breakdown):
    core_parts = [item["en"] for item in chunk_breakdown if item["is_core"]]
    if not core_parts:
        return ""
    text = " ".join(core_parts).strip()
    if text and text[-1] not in ".!?":
        text = f"{text}."
    return text


def _build_translation(chunk_breakdown):
    parts = [item["cn"] for item in chunk_breakdown if item["cn"]]
    return "，".join(parts) if parts else "自动拆解结果"


def _build_grammar_tags(sentence, words, chunk_breakdown):
    normalized_sentence = " ".join(item["lower"] for item in words).strip()
    if normalized_sentence in FIXED_EXPRESSION_TRANSLATIONS:
        return ["固定表达", "礼貌用语"]
    tags = [_infer_structure_label(chunk_breakdown), _infer_tense_label(words, chunk_breakdown)]
    if any(item["role_type"] == "clause" for item in chunk_breakdown):
        tags.append("从句")
    if any(item["role_type"] == "adverbial" for item in chunk_breakdown):
        tags.append("状语")
    if " than " in sentence.lower():
        tags.append("比较结构")
    result = []
    for item in tags:
        if item and item not in result:
            result.append(item)
    return result


def _build_summary(structure_label, tense_label, chunk_breakdown):
    if len(chunk_breakdown) == 1:
        expression = chunk_breakdown[0]["en"].strip().lower()
        if expression in FIXED_EXPRESSION_TRANSLATIONS:
            return "这是一条固定礼貌表达，整体理解它的交际功能即可，不要逐词硬译。"
    if any(item["role_type"] == "clause" for item in chunk_breakdown):
        return f"这句话建议先抓 {structure_label} 的主线，再把从句和状语作为补充信息回填。"
    if any(item["role_type"] == "complement" for item in chunk_breakdown):
        return f"这句话更接近 {structure_label}，同时要注意 {tense_label} 下主语和补语的配合。"
    if any(item["role_type"] == "object" for item in chunk_breakdown):
        return f"这句话可以先沿着 {structure_label} 去读，再补充时间、地点或方式信息。"
    return f"先抓主语和谓语，再结合 {tense_label} 看整句表达。"


def _build_analysis(main_structure, chunk_breakdown):
    if len(chunk_breakdown) == 1:
        expression = chunk_breakdown[0]["en"].strip()
        normalized_expression = expression.lower()
        if normalized_expression in FIXED_EXPRESSION_TRANSLATIONS:
            cn = FIXED_EXPRESSION_TRANSLATIONS[normalized_expression]
            return f"{expression} 是固定礼貌表达，整体理解为“{cn}”，不必拆成单词逐个硬译。"

    parts = []
    if main_structure:
        parts.append(f"先把句子主干读成 {main_structure}")

    clause_parts = [item["en"] for item in chunk_breakdown if item["role_type"] == "clause"]
    if clause_parts:
        parts.append(f"{'；'.join(clause_parts)} 需要作为附加信息回填，不要一上来就和主干混在一起。")

    adverbials = [item["en"] for item in chunk_breakdown if item["role_type"] == "adverbial"]
    if adverbials:
        parts.append(f"{'；'.join(adverbials)} 负责补充时间、地点、方式或背景。")

    complements = [item["en"] for item in chunk_breakdown if item["role_type"] == "complement"]
    if complements:
        parts.append(f"{'；'.join(complements)} 用来说明主语当前的状态、身份或结果。")

    if not parts:
        parts.append("这句话可以先抓主语和谓语，再看其他成分。")

    return " ".join(parts)


def _build_learning_tip(chunk_breakdown):
    if len(chunk_breakdown) == 1:
        expression = chunk_breakdown[0]["en"].strip().lower()
        if expression in FIXED_EXPRESSION_TRANSLATIONS:
            return "遇到固定表达时，优先整体记忆它的使用场景和语气，不要机械逐词翻译。"
    if any(item["role_type"] == "clause" for item in chunk_breakdown):
        return "阅读这类句子时，先锁定主干，再把从句当作补充层逐块回填。"
    if any(item["role_type"] == "adverbial" for item in chunk_breakdown):
        return "建议先找动作核心，再分清哪些是宾语，哪些只是时间、地点或方式信息。"
    return "先看主语和谓语，再判断动作作用到谁或说明了什么状态。"


def _build_segments_from_annotations(sentence, annotations, core_only=False):
    result = []
    cursor = 0
    for item in sorted(annotations, key=lambda annotation: (annotation["start_index"], annotation["end_index"], annotation["id"])):
        if item["start_index"] > cursor:
            result.append(
                {
                    "text": sentence[cursor : item["start_index"]],
                    "annotation_id": None,
                    "token": "plain",
                    "background": COLOR_PALETTE["plain"]["bg"],
                    "color": COLOR_PALETTE["plain"]["color"],
                    "role_label": "",
                    "grammar_label": "",
                }
            )

        if core_only and not item["is_core"]:
            result.append(
                {
                    "text": sentence[item["start_index"] : item["end_index"]],
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
                    "text": sentence[item["start_index"] : item["end_index"]],
                    "annotation_id": item["id"],
                    "token": item["color_token"],
                    "background": item["background"],
                    "color": item["color"],
                    "role_label": item["role_label"],
                    "grammar_label": item["grammar_label"],
                }
            )
        cursor = item["end_index"]

    if cursor < len(sentence):
        result.append(
            {
                "text": sentence[cursor:],
                "annotation_id": None,
                "token": "plain",
                "background": COLOR_PALETTE["plain"]["bg"],
                "color": COLOR_PALETTE["plain"]["color"],
                "role_label": "",
                "grammar_label": "",
            }
        )

    return [item for item in result if item["text"]]
