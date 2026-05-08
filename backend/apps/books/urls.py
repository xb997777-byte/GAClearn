from django.urls import path

from .views import BookDetailView, BookListView, BookWordListView, WordDetailView

urlpatterns = [
    path("books", BookListView.as_view()),
    path("books/<int:book_id>", BookDetailView.as_view()),
    path("books/<int:book_id>/words", BookWordListView.as_view()),
    path("words/<int:word_id>", WordDetailView.as_view()),
]
