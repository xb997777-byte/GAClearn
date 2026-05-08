from rest_framework.views import APIView

from apps.ai.graphs.grammar_tutor import build_grammar_tutor_answer, build_grammar_tutor_detail
from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .ai import answer_grammar_question, is_ai_available
from .analyzer import analyze_sentence_input
from .serializers import (
    GrammarAnalyzeSerializer,
    GrammarAskSerializer,
    GrammarRecommendQuerySerializer,
    GrammarRecordSerializer,
    GrammarSentenceQuerySerializer,
)
from .services import build_progress, create_learning_record, get_sentence_detail, list_points, list_recommendations, list_sentences


def _fallback_grammar_answer(sentence, question):
    detail = analyze_sentence_input(sentence, enable_ai_enrichment=False) if sentence else None
    if detail:
        return (
            f"当前后端未配置 AI 服务，先给你规则分析版参考："
            f"句子主干是“{detail.get('main_structure', '')}”，"
            f"中文释义是“{detail.get('translation_cn', '')}”。"
            f"如果你想得到更细的问答解释，请配置 AI_API_KEY、AI_MODEL 和 AI_BASE_URL。"
        )
    return "当前后端未配置 AI 服务，请先配置 AI_API_KEY、AI_MODEL 和 AI_BASE_URL 后再使用语法问答。"


class GrammarTopicView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"list": list_points(request.user)})


class GrammarSentenceListView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        serializer = GrammarSentenceQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(list_sentences(request.user, serializer.validated_data))


class GrammarSentenceDetailView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, sentence_id):
        data = get_sentence_detail(request.user, sentence_id)
        if not data:
            return error_response("sentence not found", code=40411, status_code=404)
        return success_response(data)


class GrammarSentenceAnalyzeView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = GrammarAnalyzeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            sentence = serializer.validated_data["sentence"]
            detail = analyze_sentence_input(sentence, enable_ai_enrichment=False)
            data = build_grammar_tutor_detail(request.user, sentence, detail=detail)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception:
            try:
                data = analyze_sentence_input(serializer.validated_data["sentence"])
            except ValueError as exc:
                return error_response(str(exc), code=40004)
        return success_response(data)


class GrammarAskView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = GrammarAskSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        sentence = serializer.validated_data.get("sentence", "")
        question = serializer.validated_data["question"]
        if is_ai_available():
            try:
                detail = analyze_sentence_input(sentence, enable_ai_enrichment=False) if sentence else None
                answer_payload = build_grammar_tutor_answer(request.user, sentence, question, detail=detail)
            except Exception as exc:
                try:
                    detail = analyze_sentence_input(sentence, enable_ai_enrichment=False) if sentence else None
                    answer = answer_grammar_question(sentence, question, detail)
                    answer_payload = {"answer": answer, "ai_enabled": is_ai_available(), "references": [], "followup_questions": []}
                except Exception:
                    return error_response(str(exc), code=40005)
        else:
            answer_payload = {
                "answer": _fallback_grammar_answer(sentence, question),
                "ai_enabled": is_ai_available(),
                "references": [],
                "followup_questions": [],
            }
        return success_response(answer_payload)


class GrammarRecommendView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        serializer = GrammarRecommendQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        data = list_recommendations(request.user, **serializer.validated_data)
        return success_response({"list": data})


class GrammarRecordView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = GrammarRecordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            data = create_learning_record(request.user, serializer.validated_data)
        except ValueError as exc:
            return error_response(str(exc), code=40411, status_code=404)
        return success_response(data, message="record saved")


class GrammarProgressView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(build_progress(request.user))
