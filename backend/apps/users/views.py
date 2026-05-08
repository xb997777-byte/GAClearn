from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from apps.ai.rag.personalized_runtime import sync_personalized_rag_for_user

from .models import UserFeedback
from .serializers import ProfileUpdateSerializer, UserFeedbackSubmitSerializer, UserSettingSerializer, WxLoginSerializer
from .services import ensure_user_setting, login_with_code, refresh_token, serialize_setting, serialize_user, update_profile


class WxLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = WxLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            data = login_with_code(**serializer.validated_data)
        except ValueError as exc:
            return error_response(str(exc), code=40002)
        return success_response(data)


class ProfileSyncView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(update_profile(request.user, serializer.validated_data), message="profile updated")


class RefreshTokenView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        return success_response(refresh_token(request.user, request.auth), message="token refreshed")


class CurrentUserView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(serialize_user(request.user))


class UserSettingsView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(serialize_setting(ensure_user_setting(request.user)))

    def put(self, request):
        setting = ensure_user_setting(request.user)
        serializer = UserSettingSerializer(instance=setting, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        serializer.save()
        return success_response(serialize_setting(setting), message="settings updated")


class PersonalizedRagRebuildView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        setting = ensure_user_setting(request.user)
        if not setting.personalized_rag_enabled:
            return error_response("请先在学习设置中开启个性化 RAG", code=40003)

        try:
            result = sync_personalized_rag_for_user(request.user)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)

        return success_response(
            {
                "result": result,
                "settings": serialize_setting(ensure_user_setting(request.user)),
            },
            message="personalized rag synced",
        )


class UserFeedbackView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = UserFeedbackSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        feedback = UserFeedback.objects.create(user=request.user, **serializer.validated_data)
        return success_response(
            {
                "id": feedback.id,
                "status": feedback.status,
                "created_at": feedback.created_at,
            },
            message="feedback submitted",
            status_code=201,
        )
