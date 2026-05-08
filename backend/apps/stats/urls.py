from django.urls import path

from .views import CheckinHistoryView, CheckinView, StatsOverviewView, StatsTrendView

urlpatterns = [
    path("stats/overview", StatsOverviewView.as_view(), name="stats-overview"),
    path("stats/trend", StatsTrendView.as_view(), name="stats-trend"),
    path("checkin", CheckinView.as_view(), name="checkin"),
    path("checkin/history", CheckinHistoryView.as_view(), name="checkin-history"),
]
