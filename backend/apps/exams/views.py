from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .serializers import PlacementGenerateSerializer, TestGenerateSerializer, TestSubmitSerializer
from .services import (
    generate_placement_test,
    generate_test,
    get_test_result,
    list_test_history,
    submit_placement_test,
    submit_test,
)


class TestGenerateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = TestGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            data = generate_test(
                request.user,
                serializer.validated_data["question_count"],
                serializer.validated_data.get("book_id"),
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(data)


class PlacementGenerateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = PlacementGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(generate_placement_test(request.user, serializer.validated_data["question_count"]))


class TestSubmitView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = TestSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            data = submit_test(request.user, serializer.validated_data["test_id"], serializer.validated_data["answers"])
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(data)


class PlacementSubmitView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = TestSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            data = submit_placement_test(request.user, serializer.validated_data["test_id"], serializer.validated_data["answers"])
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(data)


class TestResultView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, test_id):
        return success_response(get_test_result(request.user, test_id))


class TestHistoryView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"list": list_test_history(request.user)})
