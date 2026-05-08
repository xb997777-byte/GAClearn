from django.urls import path

from .views import FavoriteDeleteView, FavoriteListCreateView, LearnWordDetailView, LearnWordListView, LearningRecordBatchView, LearningRecordView

urlpatterns = [
    path("learn/words", LearnWordListView.as_view(), name="learn-words"),
    path("learn/words/<int:word_id>", LearnWordDetailView.as_view(), name="learn-word-detail"),
    path("learn/records", LearningRecordView.as_view(), name="learn-records"),
    path("learn/records/batch", LearningRecordBatchView.as_view(), name="learn-records-batch"),
    path("favorites", FavoriteListCreateView.as_view(), name="favorites"),
    path("favorites/<int:word_id>", FavoriteDeleteView.as_view(), name="favorite-delete"),
]
