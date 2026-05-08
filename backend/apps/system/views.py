from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.grammar.ai import is_ai_available
from apps.users.wechat import get_wechat_login_mode, has_wechat_credentials, list_subscribe_template_ids
from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .serializers import SpeechSynthesizeSerializer
from .speech import SpeechSynthesisError, build_speech_payload


class ApiRootView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return success_response(
            {
                "project": "wxapp english learn backend api",
                "version": "v1",
                "docs_file": "3-架构设计/3-项目接口文档.md",
                "endpoints": {
                    "auth": "/api/v1/auth/wx-login",
                    "books": "/api/v1/books",
                    "plans": "/api/v1/plans/current",
                    "learn": "/api/v1/learn/words",
                    "review": "/api/v1/review/tasks",
                    "tests": "/api/v1/tests/generate",
                    "placement": "/api/v1/tests/placement/generate",
                    "grammar_ai": "/api/v1/grammar/ask",
                    "stats": "/api/v1/stats/overview",
                    "bootstrap": "/api/v1/system/bootstrap",
                    "health": "/api/v1/system/ping",
                    "speech": "/api/v1/system/speech",
                },
            }
        )


class HealthPingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return success_response({"status": "ok"})


class SystemBootstrapView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        reminder_template_ids = list_subscribe_template_ids()
        return success_response(
            {
                "features": {
                    "wechat_login_mode": get_wechat_login_mode(),
                    "wechat_login_enabled": has_wechat_credentials(),
                    "subscribe_reminder_enabled": bool(reminder_template_ids),
                    "subscribe_template_ids": reminder_template_ids,
                    "ai_enabled": is_ai_available(),
                }
            }
        )


class SystemSpeechView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = SpeechSynthesizeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        try:
            data = build_speech_payload(
                request,
                serializer.validated_data["text"],
                serializer.validated_data.get("lang", "en-US"),
                serializer.validated_data.get("speed", 1.0),
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except SpeechSynthesisError as exc:
            return error_response(str(exc), code=50021, status_code=500)
        return success_response(data)
