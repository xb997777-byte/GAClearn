from django.urls import path

from .views import ReviewResultView, ReviewSubmitView, ReviewTaskView, WrongWordDeleteView, WrongWordListView

urlpatterns = [
    path("review/tasks", ReviewTaskView.as_view(), name="review-tasks"),
    path("review/submit", ReviewSubmitView.as_view(), name="review-submit"),
    path("review/result/<int:session_id>", ReviewResultView.as_view(), name="review-result"),
    path("wrong-words", WrongWordListView.as_view(), name="wrong-words"),
    path("wrong-words/<int:word_id>", WrongWordDeleteView.as_view(), name="wrong-word-delete"),
]
