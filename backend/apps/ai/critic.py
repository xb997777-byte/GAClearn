from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .response_contracts import normalize_feature_contract


@dataclass
class CriticResult:
    ok: bool
    summary: str
    issues: List[str] = field(default_factory=list)
    repaired_payload: Dict[str, Any] = field(default_factory=dict)
    degraded: bool = False


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def _repair_minimal_fields(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    repaired = dict(payload or {})
    repaired.setdefault("headline", repaired.get("headline") or "AI 结果")
    repaired.setdefault("summary", repaired.get("summary") or "AI 已返回结果。")
    if feature_type in {"rag_search", "vector_rag"}:
        answer_brief = dict(repaired.get("answer_brief") or {})
        answer_brief.setdefault("summary", repaired.get("summary") or "AI 已返回结果。")
        answer_brief.setdefault("points", [])
        answer_brief.setdefault("next_questions", ["换个问法再试", "查看依据"])
        repaired["answer_brief"] = answer_brief
        repaired.setdefault("documents", [])
        repaired.setdefault("evidence", {})
    if feature_type == "conversation":
        repaired.setdefault("resolved_route", repaired.get("resolved_route") or "rag")
        repaired.setdefault("assistant_message", {"content": repaired.get("summary") or "AI 已返回结果。"})
    return normalize_feature_contract(feature_type, repaired)


def run_feature_critic(
    *,
    feature_type: str,
    payload: Dict[str, Any],
    require_evidence: bool = False,
    require_answer_brief: bool = False,
) -> CriticResult:
    issues: List[str] = []
    if not isinstance(payload, dict):
        return CriticResult(
            ok=False,
            summary="输出不是合法对象，已进入修复。",
            issues=["payload_not_dict"],
            repaired_payload=_repair_minimal_fields(feature_type, {}),
            degraded=True,
        )
    if _is_blank(payload.get("headline")):
        issues.append("missing_headline")
    if _is_blank(payload.get("summary")):
        issues.append("missing_summary")
    if require_answer_brief:
        answer_brief = payload.get("answer_brief") or {}
        if _is_blank((answer_brief or {}).get("summary")):
            issues.append("missing_answer_brief")
    if require_evidence and _is_blank(payload.get("documents")) and _is_blank(payload.get("evidence")):
        issues.append("missing_grounding")
    if feature_type == "conversation" and _is_blank(payload.get("assistant_message")):
        issues.append("missing_assistant_message")
    if not issues:
        return CriticResult(ok=True, summary="critic 校验通过。", repaired_payload=payload)
    repaired = _repair_minimal_fields(feature_type, payload)
    remaining = []
    if _is_blank(repaired.get("headline")):
        remaining.append("missing_headline")
    if _is_blank(repaired.get("summary")):
        remaining.append("missing_summary")
    if require_answer_brief and _is_blank((repaired.get("answer_brief") or {}).get("summary")):
        remaining.append("missing_answer_brief")
    if require_evidence and _is_blank(repaired.get("documents")) and _is_blank(repaired.get("evidence")):
        remaining.append("missing_grounding")
    if feature_type == "conversation" and _is_blank(repaired.get("assistant_message")):
        remaining.append("missing_assistant_message")
    return CriticResult(
        ok=not remaining,
        summary="critic 已完成结构检查并尝试修复。",
        issues=issues if remaining else [],
        repaired_payload=repaired,
        degraded=bool(remaining),
    )
