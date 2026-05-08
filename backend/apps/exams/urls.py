from django.urls import path

from .views import PlacementGenerateView, PlacementSubmitView, TestGenerateView, TestHistoryView, TestResultView, TestSubmitView

urlpatterns = [
    path("tests/generate", TestGenerateView.as_view(), name="tests-generate"),
    path("tests/placement/generate", PlacementGenerateView.as_view(), name="tests-placement-generate"),
    path("tests/submit", TestSubmitView.as_view(), name="tests-submit"),
    path("tests/placement/submit", PlacementSubmitView.as_view(), name="tests-placement-submit"),
    path("tests/result/<int:test_id>", TestResultView.as_view(), name="tests-result"),
    path("tests/history", TestHistoryView.as_view(), name="tests-history"),
]
