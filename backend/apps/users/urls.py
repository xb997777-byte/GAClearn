from django.urls import path

from .views import (
    CurrentUserView,
    PersonalizedRagRebuildView,
    ProfileSyncView,
    RefreshTokenView,
    UserFeedbackView,
    UserSettingsView,
    WxLoginView,
)

urlpatterns = [
    path("auth/wx-login", WxLoginView.as_view()),
    path("auth/profile", ProfileSyncView.as_view()),
    path("auth/refresh", RefreshTokenView.as_view()),
    path("users/me", CurrentUserView.as_view()),
    path("users/settings", UserSettingsView.as_view()),
    path("users/settings/personalized-rag/rebuild", PersonalizedRagRebuildView.as_view()),
    path("users/feedback", UserFeedbackView.as_view()),
]
