from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.responses import error_response, success_response

from .serializers import BookSerializer, WordSerializer
from .services import get_book_detail, get_word, list_book_words, list_books, paginate_queryset


class BookListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        books, total, page, page_size = paginate_queryset(
            list_books(
                category=request.query_params.get("category"),
                keyword=request.query_params.get("keyword"),
                level=request.query_params.get("level"),
            ),
            page=page,
            page_size=page_size,
        )
        return success_response(
            {
                "list": BookSerializer(books, many=True).data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                },
            }
        )


class BookDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, book_id):
        book = get_book_detail(book_id)
        if not book:
            return error_response("book not found", code=40401, status_code=404)
        return success_response(BookSerializer(book).data)


class BookWordListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, book_id):
        book = get_book_detail(book_id)
        if not book:
            return error_response("book not found", code=40401, status_code=404)
        words, total, page, page_size = list_book_words(
            book,
            page=request.query_params.get("page", 1),
            page_size=request.query_params.get("page_size", 20),
            keyword=request.query_params.get("keyword"),
        )
        return success_response(
            {
                "items": WordSerializer(words, many=True).data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                },
            }
        )


class WordDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, word_id):
        word = get_word(word_id)
        if not word:
            return error_response("word not found", code=40402, status_code=404)
        return success_response(WordSerializer(word).data)
