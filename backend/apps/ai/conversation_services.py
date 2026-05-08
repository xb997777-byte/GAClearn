from django.shortcuts import get_object_or_404

from .evidence import attach_feature_evidence
from .graphs.grammar_tutor import build_grammar_tutor_answer, build_grammar_tutor_detail
from .learning_assistant import correct_writing, evaluate_translation, run_rag_search
from .models import AIConversation, AIMessage, AIUserFeedback
from .response_contracts import normalize_feature_contract


def serialize_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "payload": message.payload,
        "prompt_version": message.prompt_version,
        "model_name": message.model_name,
        "latency_ms": message.latency_ms,
        "created_at": message.created_at,
    }


def serialize_conversation(conversation, include_messages=False):
    data = {
        "id": conversation.id,
        "feature_type": conversation.feature_type,
        "title": conversation.title,
        "context": conversation.context,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }
    if include_messages:
        data["messages"] = [serialize_message(item) for item in conversation.messages.order_by("id")]
    return data


def list_conversations(user, feature_type="", limit=20):
    queryset = AIConversation.objects.filter(user=user)
    if feature_type:
        queryset = queryset.filter(feature_type=feature_type)
    return [serialize_conversation(item) for item in queryset.order_by("-id")[: min(max(int(limit or 20), 1), 50)]]


def get_conversation_detail(user, conversation_id):
    conversation = get_object_or_404(AIConversation, id=conversation_id, user=user)
    return serialize_conversation(conversation, include_messages=True)


def create_conversation(user, feature_type, title="", context=None):
    return serialize_conversation(
        AIConversation.objects.create(
            user=user,
            feature_type=feature_type,
            title=title or "新的 AI 会话",
            context={"feature_type": feature_type, **(context or {})},
        ),
        include_messages=True,
    )


def _resolve_conversation_feature(conversation, feature_type):
    if conversation and conversation.feature_type:
        return conversation.feature_type
    return (feature_type or "rag").strip() or "rag"


def _looks_like_grammar_followup(text):
    question = str(text or "").strip()
    if not question:
        return False
    lowered = question.lower()
    chinese_markers = ["为什么", "怎么", "哪里", "什么意思", "区别", "语法", "解释", "能不能"]
    english_prefixes = ("why ", "what ", "how ", "which ", "can ", "could ", "should ", "please ")
    return any(marker in question for marker in chinese_markers) or lowered.startswith(english_prefixes)


def _extract_translation_inputs(question, context):
    text = str(question or "").strip()
    if not text:
        return "", ""

    source_text = ""
    user_translation = ""
    lines = [item.strip() for item in text.splitlines() if item.strip()]

    for line in lines:
        if line.startswith("原文：") or line.startswith("原文:"):
            source_text = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
        elif line.startswith("译文：") or line.startswith("译文:") or line.startswith("我的翻译：") or line.startswith("我的翻译:"):
            user_translation = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]

    if not source_text and len(lines) >= 2:
        source_text = lines[0]
        user_translation = "\n".join(lines[1:])

    if not source_text and "=>" in text:
        left, right = text.split("=>", 1)
        source_text = left.strip()
        user_translation = right.strip()

    if not source_text:
        source_text = text
        user_translation = context.get("last_user_translation", "")

    return source_text, user_translation


def _run_feature_answer(user, feature_type, question, conversation):
    feature_key = _resolve_conversation_feature(conversation, feature_type)
    context = dict((conversation.context if conversation else {}) or {})
    next_context = dict(context)

    if feature_key == "grammar":
        current_sentence = str(context.get("current_sentence", "")).strip()
        if current_sentence and _looks_like_grammar_followup(question):
            result = build_grammar_tutor_answer(user, current_sentence, question)
        else:
            result = build_grammar_tutor_detail(user, question)
            current_sentence = result.get("sentence") or question
        next_context["current_sentence"] = current_sentence
        runtime_feature = "grammar_tutor"
    elif feature_key == "writing":
        result = correct_writing(user, question, level=context.get("level", "cet4") or "cet4")
        next_context["last_text"] = question
        runtime_feature = "writing_correct"
    elif feature_key == "translation":
        source_text, user_translation = _extract_translation_inputs(question, context)
        result = evaluate_translation(user, source_text, user_translation, direction="auto")
        next_context["last_source_text"] = source_text
        next_context["last_user_translation"] = user_translation
        runtime_feature = "translation_evaluate"
    else:
        result = run_rag_search(question)
        runtime_feature = "rag_search"

    attach_feature_evidence(runtime_feature, result)
    normalize_feature_contract(runtime_feature, result)
    return feature_key, result, next_context


def _build_assistant_content(feature_type, result):
    if feature_type == "grammar":
        tutor = result.get("tutor") or {}
        return tutor.get("explanation_cn") or result.get("answer") or result.get("summary") or "已经生成语法讲解。"
    if feature_type == "writing":
        writing = result.get("result") or {}
        return writing.get("overall_feedback") or result.get("summary") or "已经完成写作批改。"
    if feature_type == "translation":
        translation = result.get("result") or {}
        return translation.get("feedback") or result.get("summary") or "已经生成翻译训练反馈。"
    answer_payload = result.get("answer") or {}
    return answer_payload.get("summary") or result.get("summary") or "已经根据当前学习资料生成回答。"


def ask_conversation(user, question, conversation_id=None, feature_type="rag"):
    if conversation_id:
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=user)
    else:
        feature_key = (feature_type or "rag").strip() or "rag"
        conversation = AIConversation.objects.create(
            user=user,
            feature_type=feature_key,
            title=question[:48] or "AI 学习问答",
            context={"source": "conversation", "feature_type": feature_key},
        )
    user_message = AIMessage.objects.create(conversation=conversation, role="user", content=question)
    feature_key, result, next_context = _run_feature_answer(user, feature_type, question, conversation)
    if next_context != (conversation.context or {}):
        conversation.context = next_context
        conversation.save(update_fields=["context", "updated_at"])
    content = _build_assistant_content(feature_key, result)
    assistant_message = AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=content,
        payload=result,
        prompt_version=result.get("ai_strategy", {}).get("prompt_version", ""),
        model_name=result.get("ai_strategy", {}).get("model_name", ""),
        latency_ms=int((result.get("ai_observability") or {}).get("latency_ms") or 0),
    )
    return {
        "conversation": serialize_conversation(conversation),
        "user_message": serialize_message(user_message),
        "assistant_message": serialize_message(assistant_message),
        "answer": result,
    }


def create_ai_feedback(user, data):
    conversation = None
    message = None
    conversation_id = data.get("conversation_id")
    message_id = data.get("message_id")
    if conversation_id:
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=user)
    if message_id:
        message = get_object_or_404(AIMessage, id=message_id, conversation__user=user)
    feedback = AIUserFeedback.objects.create(
        user=user,
        conversation=conversation,
        message=message,
        feature_type=data.get("feature_type", "") or (conversation.feature_type if conversation else ""),
        rating=data.get("rating", "helpful"),
        content=data.get("content", ""),
        payload=data.get("payload", {}),
    )
    return {
        "id": feedback.id,
        "feature_type": feedback.feature_type,
        "rating": feedback.rating,
        "content": feedback.content,
        "created_at": feedback.created_at,
    }
