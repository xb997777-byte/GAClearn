from django.urls import path

from .views import (
    CurrentPlanView,
    CurrentPlanApplyAIPatchView,
    CurrentPlanHistoryView,
    CurrentPlanRollbackView,
    PlanCreateView,
    SwitchBookView,
    TodayTaskFinishView,
    TodayTaskStartView,
    TodayTaskView,
)

urlpatterns = [
    path("plans/current", CurrentPlanView.as_view()),
    path("plans/current/history", CurrentPlanHistoryView.as_view()),
    path("plans/current/apply-ai-patch", CurrentPlanApplyAIPatchView.as_view()),
    path("plans/current/rollback", CurrentPlanRollbackView.as_view()),
    path("plans", PlanCreateView.as_view()),
    path("plans/current/switch-book", SwitchBookView.as_view()),
    path("tasks/today", TodayTaskView.as_view()),
    path("tasks/today/start", TodayTaskStartView.as_view()),
    path("tasks/today/finish", TodayTaskFinishView.as_view()),
]
