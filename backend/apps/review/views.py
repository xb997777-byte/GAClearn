from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .serializers import ReviewSubmitSerializer
from .services import generate_review_tasks, get_review_result, list_wrong_words, remove_wrong_word, submit_review


class ReviewTaskView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        return success_response(generate_review_tasks(request.user, limit))


class ReviewSubmitView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = ReviewSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(submit_review(request.user, serializer.validated_data["session_id"], serializer.validated_data["answers"]))


class ReviewResultView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, session_id):
        return success_response(get_review_result(request.user, session_id))


class WrongWordListView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"list": list_wrong_words(request.user)})


class WrongWordDeleteView(APIView):
    permission_classes = [IsWxAuthenticated]

    def delete(self, request, word_id):
        remove_wrong_word(request.user, word_id)
        return success_response({"word_id": word_id})
