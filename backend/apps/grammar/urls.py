from django.urls import path

from .views import (
    GrammarAskView,
    GrammarProgressView,
    GrammarRecordView,
    GrammarSentenceAnalyzeView,
    GrammarRecommendView,
    GrammarSentenceDetailView,
    GrammarSentenceListView,
    GrammarTopicView,
)

urlpatterns = [
    path("grammar/topics", GrammarTopicView.as_view(), name="grammar-topics"),
    path("grammar/analyze", GrammarSentenceAnalyzeView.as_view(), name="grammar-analyze"),
    path("grammar/ask", GrammarAskView.as_view(), name="grammar-ask"),
    path("grammar/sentences", GrammarSentenceListView.as_view(), name="grammar-sentences"),
    path("grammar/sentences/recommend", GrammarRecommendView.as_view(), name="grammar-recommend"),
    path("grammar/sentences/<int:sentence_id>", GrammarSentenceDetailView.as_view(), name="grammar-sentence-detail"),
    path("grammar/records", GrammarRecordView.as_view(), name="grammar-records"),
    path("grammar/progress", GrammarProgressView.as_view(), name="grammar-progress"),
]
