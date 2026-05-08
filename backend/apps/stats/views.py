from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .serializers import TrendQuerySerializer
from .services import build_overview, build_trend, list_checkin_history, perform_checkin


class StatsOverviewView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(build_overview(request.user))


class StatsTrendView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        serializer = TrendQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response({"list": build_trend(request.user, serializer.validated_data["days"])})


class CheckinView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        return success_response(perform_checkin(request.user))


class CheckinHistoryView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"list": list_checkin_history(request.user)})
