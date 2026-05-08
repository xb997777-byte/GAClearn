import json
import os
from datetime import datetime, time, timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from apps.grammar.models import GrammarLearningRecord
from apps.learn.models import LearningRecord
from apps.review.models import ReviewRecord, WrongWord
from apps.stats.services import build_overview, build_trend

from .models import AIStudyReport
from .providers.deepseek import chat_json, is_provider_ready
from .tools.study_tools import build_study_coach_bundle


PROMPT_VERSION = "report_v1"


def _json_safe(value):
    return json.loads(json.dumps(value, ensure_ascii=False, cls=DjangoJSONEncoder))


def _date_range(report_type):
    today = timezone.localdate()
    days = 30 if report_type == "monthly" else 7
    return today - timedelta(days=days - 1), today, days


def _build_period_snapshot(user, report_type):
    period_start, period_end, days = _date_range(report_type)
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(period_start, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(period_end + timedelta(days=1), time.min), tz)
    review_total = ReviewRecord.objects.filter(user=user, reviewed_at__gte=start_dt, reviewed_at__lt=end_dt).count()
    review_correct = ReviewRecord.objects.filter(
        user=user,
        reviewed_at__gte=start_dt,
        reviewed_at__lt=end_dt,
        is_correct=True,
    ).count()
    return {
        "report_type": report_type,
        "period_start": period_start,
        "period_end": period_end,
        "overview": build_overview(user),
        "trend": build_trend(user, days=days),
        "period_metrics": {
            "learn_records": LearningRecord.objects.filter(user=user, occurred_at__gte=start_dt, occurred_at__lt=end_dt).count(),
            "review_total": review_total,
            "review_correct": review_correct,
            "review_accuracy": round((review_correct / review_total) * 100, 2) if review_total else 0,
            "grammar_records": GrammarLearningRecord.objects.filter(user=user, occurred_at__gte=start_dt, occurred_at__lt=end_dt).count(),
            "active_wrong_words": WrongWord.objects.filter(user=user, is_active=True).count(),
        },
        "coach_bundle": build_study_coach_bundle(user, trend_days=min(days, 14)),
    }


def _build_report_fallback(snapshot):
    metrics = snapshot["period_metrics"]
    overview = snapshot["overview"]
    report_label = "月报" if snapshot["report_type"] == "monthly" else "周报"
    return {
        "headline": f"你的英语学习{report_label}已生成",
        "summary": (
            f"本周期完成 {metrics['learn_records']} 条学习记录、{metrics['review_total']} 次复习，"
            f"复习正确率 {metrics['review_accuracy']}%。"
        ),
        "wins": [
            f"累计学习 {overview.get('learned_word_count', 0)} 个词。",
            f"当前连续学习 {overview.get('streak_days', 0)} 天。",
            f"语法学习进度 {overview.get('grammar_learning_percent', 0)}%。",
        ],
        "risks": [
            f"当前仍有 {metrics['active_wrong_words']} 个活跃错词，需要安排回收。",
            "如果复习正确率低于 80%，建议先减少新词并增加例句复盘。",
        ],
        "next_plan": [
            "先完成到期复习，再推进新词。",
            "每天挑 3 个错词做例句复述。",
            "用语法例句补一次长句理解训练。",
        ],
        "focus_words_hint": "优先处理错词本里重复出错次数最高的词。",
        "motivation": "稳定的小步推进，比一次性冲刺更容易留下长期记忆。",
    }


def _generate_report_with_ai(snapshot):
    if not is_provider_ready():
        return _build_report_fallback(snapshot)
    payload = {
        "snapshot": snapshot,
        "task": "Create a concise Chinese English-learning weekly/monthly report. Return strict JSON only.",
        "output_schema": {
            "headline": "string",
            "summary": "string",
            "wins": ["string"],
            "risks": ["string"],
            "next_plan": ["string"],
            "focus_words_hint": "string",
            "motivation": "string",
        },
    }
    fallback = _build_report_fallback(snapshot)
    try:
        result = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an English learning analyst for Chinese learners. "
                        "Base the report only on the provided data and return strict JSON."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
            ],
            temperature=0.25,
        )
        fallback.update({key: result.get(key) or fallback[key] for key in fallback})
    except Exception as exc:
        fallback["provider_error"] = str(exc)
    return fallback


def generate_study_report(user, report_type="weekly"):
    report_type = report_type if report_type in {"weekly", "monthly"} else "weekly"
    snapshot = _build_period_snapshot(user, report_type)
    summary = _generate_report_with_ai(snapshot)
    report, _ = AIStudyReport.objects.update_or_create(
        user=user,
        report_type=report_type,
        period_start=snapshot["period_start"],
        period_end=snapshot["period_end"],
        defaults={
            "title": summary.get("headline", ""),
            "summary": _json_safe(summary),
            "source_snapshot": _json_safe(snapshot),
        },
    )
    return serialize_report(report)


def serialize_report(report):
    return {
        "id": report.id,
        "report_type": report.report_type,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "title": report.title,
        "summary": report.summary,
        "source_snapshot": report.source_snapshot,
        "created_at": report.created_at,
        "ai_strategy": {
            "engine": "pipeline",
            "rag_enabled": True,
            "ai_enabled": is_provider_ready(),
            "prompt_version": PROMPT_VERSION,
            "model_name": os.getenv("AI_MODEL", "").strip(),
        },
    }


def _build_compare_summary(current_report, previous_report):
    current_snapshot = current_report.source_snapshot or {}
    previous_snapshot = previous_report.source_snapshot or {}
    current_metrics = current_snapshot.get("period_metrics") or {}
    previous_metrics = previous_snapshot.get("period_metrics") or {}
    current_overview = current_snapshot.get("overview") or {}
    previous_overview = previous_snapshot.get("overview") or {}

    def _delta(current_value, previous_value):
        return current_value - previous_value

    learn_delta = _delta(current_metrics.get("learn_records", 0), previous_metrics.get("learn_records", 0))
    accuracy_delta = round(
        (current_metrics.get("review_accuracy", 0) or 0) - (previous_metrics.get("review_accuracy", 0) or 0),
        2,
    )
    wrong_word_delta = _delta(current_metrics.get("active_wrong_words", 0), previous_metrics.get("active_wrong_words", 0))
    learned_word_delta = _delta(current_overview.get("learned_word_count", 0), previous_overview.get("learned_word_count", 0))
    trend_summary = "与上一期基本持平。"
    if learn_delta > 0 or accuracy_delta > 0:
        trend_summary = "整体比上一期更积极，学习量或正确率有提升。"
    if learn_delta < 0 and accuracy_delta < 0:
        trend_summary = "本期学习节奏和准确率都偏弱，建议先稳住复习。"
    return {
        "previous_report_id": previous_report.id,
        "trend_summary": trend_summary,
        "deltas": {
            "learn_records": learn_delta,
            "review_accuracy": accuracy_delta,
            "active_wrong_words": wrong_word_delta,
            "learned_word_count": learned_word_delta,
        },
    }


def list_study_reports(user, report_type="", limit=10, include_compare=False):
    queryset = AIStudyReport.objects.filter(user=user)
    if report_type in {"weekly", "monthly"}:
        queryset = queryset.filter(report_type=report_type)
    reports = list(queryset.order_by("-period_end", "-id")[: min(max(int(limit or 10), 1), 30)])
    result = []
    for index, item in enumerate(reports):
        data = serialize_report(item)
        if include_compare:
            previous_report = reports[index + 1] if index + 1 < len(reports) else None
            data["compare_summary"] = _build_compare_summary(item, previous_report) if previous_report else None
        result.append(data)
    return result
