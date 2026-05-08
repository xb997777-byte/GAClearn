from django.shortcuts import render


def home_view(request):
    return render(
        request,
        "home.html",
        {
            "title": "英语单词学习系统",
            "admin_url": "/admin/",
            "api_url": "/api/v1/",
            "health_url": "/api/v1/system/ping",
        },
    )
