import json
import os

import requests


DEFAULT_TIMEOUT = 25


def is_ai_available():
    return bool(os.getenv("AI_API_KEY", "").strip()) and bool(os.getenv("AI_MODEL", "").strip())


def _chat(messages, temperature=0.2):
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    if not api_key or not model:
        raise RuntimeError("AI service is not configured")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": temperature,
            "messages": messages,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("AI response is empty")
    content = ((choices[0] or {}).get("message") or {}).get("content", "")
    if not content:
        raise RuntimeError("AI message content is empty")
    return content.strip()


def _extract_json_block(content):
    content = (content or "").strip()
    if content.startswith("```"):
        parts = content.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate
    return content


def _deduplicate_tags(values):
    seen = set()
    result = []
    for item in values or []:
        tag = str(item or "").strip()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def enrich_sentence_analysis(sentence_text, draft_result):
    if not is_ai_available():
        return draft_result

    prompt = {
        "sentence": sentence_text,
        "draft": {
            "translation_cn": draft_result.get("translation_cn", ""),
            "summary": draft_result.get("summary", ""),
            "analysis": draft_result.get("analysis", ""),
            "main_structure": draft_result.get("main_structure", ""),
            "grammar_tags": draft_result.get("grammar_tags", []),
            "chunk_breakdown": [
                {
                    "en": item.get("en", ""),
                    "cn": item.get("cn", ""),
                    "role_label": item.get("role_label", ""),
                    "note": item.get("note", ""),
                }
                for item in draft_result.get("chunk_breakdown", [])
            ],
        },
        "task": "Return refined Chinese explanation and keep JSON only.",
        "output_schema": {
            "translation_cn": "string",
            "summary": "string",
            "analysis": "string",
            "main_structure": "string",
            "grammar_tags": ["string"],
            "learning_tip": "string",
            "chunk_notes": [{"en": "string", "cn": "string", "note": "string"}],
        },
    }
    content = _chat(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert English grammar tutor. "
                    "Polish sentence analysis for Chinese learners. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False),
            },
        ]
    )
    payload = json.loads(_extract_json_block(content))

    enriched = dict(draft_result)
    if payload.get("translation_cn"):
        enriched["translation_cn"] = payload["translation_cn"]
    if payload.get("summary"):
        enriched["summary"] = payload["summary"]
    if payload.get("analysis"):
        enriched["analysis"] = payload["analysis"]
    if payload.get("main_structure"):
        enriched["main_structure"] = payload["main_structure"]
    if payload.get("grammar_tags"):
        enriched["grammar_tags"] = _deduplicate_tags(payload["grammar_tags"])

    point_detail = dict(enriched.get("point_detail") or {})
    if payload.get("learning_tip"):
        point_detail["learning_tip"] = payload["learning_tip"]
    enriched["point_detail"] = point_detail

    chunk_notes = payload.get("chunk_notes") or []
    if chunk_notes and enriched.get("chunk_breakdown"):
        merged_chunks = []
        for index, item in enumerate(enriched["chunk_breakdown"]):
            patch = chunk_notes[index] if index < len(chunk_notes) else {}
            merged = dict(item)
            if patch.get("cn"):
                merged["cn"] = patch["cn"]
            if patch.get("note"):
                merged["note"] = patch["note"]
            merged_chunks.append(merged)
        enriched["chunk_breakdown"] = merged_chunks

    enriched["analysis_mode"] = "ai"
    return enriched


def answer_grammar_question(sentence_text, question, detail=None):
    if not is_ai_available():
        raise RuntimeError("AI service is not configured")

    payload = {
        "sentence": sentence_text or "",
        "question": question,
        "detail": {
            "translation_cn": (detail or {}).get("translation_cn", ""),
            "summary": (detail or {}).get("summary", ""),
            "main_structure": (detail or {}).get("main_structure", ""),
            "grammar_tags": (detail or {}).get("grammar_tags", []),
        },
    }
    return _chat(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert English grammar tutor for Chinese learners. "
                    "Answer in concise Chinese. "
                    "If a sentence is provided, explain based on that sentence."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ],
        temperature=0.35,
    )
