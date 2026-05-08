from django.urls import include, path

urlpatterns = [
    path("", include("apps.system.urls")),
    path("", include("apps.ai.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.books.urls")),
    path("", include("apps.plans.urls")),
    path("", include("apps.learn.urls")),
    path("", include("apps.review.urls")),
    path("", include("apps.exams.urls")),
    path("", include("apps.grammar.urls")),
    path("", include("apps.stats.urls")),
]
