from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .serializers import FavoriteSerializer, LearningRecordBatchSerializer, LearningRecordSerializer
from .services import add_favorite, create_record, create_record_batch, delete_favorite, get_today_words, get_word_detail, list_favorites


class LearnWordListView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        raw_limit = request.query_params.get("limit", "")
        try:
            limit = int(raw_limit or 0)
        except (TypeError, ValueError):
            limit = 0
        return success_response(get_today_words(request.user, limit))


class LearnWordDetailView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, word_id):
        return success_response(get_word_detail(request.user, word_id))


class LearningRecordView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = LearningRecordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(create_record(request.user, serializer.validated_data))


class LearningRecordBatchView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = LearningRecordBatchSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response({"list": create_record_batch(request.user, serializer.validated_data["records"])})


class FavoriteListCreateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"list": list_favorites(request.user)})

    def post(self, request):
        serializer = FavoriteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(add_favorite(request.user, serializer.validated_data["word_id"], serializer.validated_data.get("note", "")))


class FavoriteDeleteView(APIView):
    permission_classes = [IsWxAuthenticated]

    def delete(self, request, word_id):
        delete_favorite(request.user, word_id)
        return success_response({"word_id": word_id})
