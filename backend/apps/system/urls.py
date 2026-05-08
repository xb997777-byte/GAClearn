from django.urls import path

from .views import ApiRootView, HealthPingView, SystemBootstrapView, SystemSpeechView

urlpatterns = [
    path("", ApiRootView.as_view()),
    path("system/bootstrap", SystemBootstrapView.as_view()),
    path("system/ping", HealthPingView.as_view()),
    path("system/speech", SystemSpeechView.as_view()),
]
