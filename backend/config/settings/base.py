import os
from pathlib import Path

import pymysql
from config.env import load_env_files

pymysql.install_as_MySQLdb()

load_env_files()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-wxapp-english-learn-dev-secret-key",
)
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "simpleui",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.ai",
    "apps.users",
    "apps.books",
    "apps.plans",
    "apps.learn",
    "apps.review",
    "apps.exams",
    "apps.grammar",
    "apps.stats",
    "apps.system",
    "apps.ops",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DB", "wxappEnglishlearn"),
        "USER": os.getenv("MYSQL_USER", "root"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", "199977"),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": int(os.getenv("MYSQL_PORT", "3306")),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "common.core.authentication.WxTokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

SIMPLEUI_HOME_TITLE = "英语单词学习后台"
SIMPLEUI_HOME_ICON = "fa fa-dashboard"
SIMPLEUI_DEFAULT_ICON = False
SIMPLEUI_HOME_INFO = False
SIMPLEUI_ANALYSIS = False

SIMPLEUI_ICON = {
    "用户与权限": "fas fa-users",
    "内容中心": "fas fa-book",
    "学习计划": "fas fa-calendar-check",
    "学习流程": "fas fa-graduation-cap",
    "AI能力": "fas fa-robot",
    "测试与统计": "fas fa-chart-line",
    "语法学习": "fas fa-language",
    "系统管理": "fas fa-cogs",
}

SIMPLEUI_CONFIG = {
    "system_keep": False,
    "dynamic": False,
    "menu_display": [
        "用户与权限",
        "内容中心",
        "学习计划",
        "学习流程",
        "AI能力",
        "语法学习",
        "测试与统计",
        "系统管理",
    ],
    "menus": [
        {
            "name": "用户与权限",
            "icon": "fas fa-users",
            "models": [
                {"name": "小程序用户", "icon": "fas fa-user", "url": "/admin/users/wxuser/"},
                {"name": "用户设置", "icon": "fas fa-sliders-h", "url": "/admin/users/usersetting/"},
                {"name": "登录令牌", "icon": "fas fa-key", "url": "/admin/users/logintoken/"},
                {"name": "意见反馈", "icon": "fas fa-comment-dots", "url": "/admin/users/userfeedback/"},
                {"name": "后台用户", "icon": "fas fa-user-shield", "url": "/admin/auth/user/"},
                {"name": "后台用户组", "icon": "fas fa-users-cog", "url": "/admin/auth/group/"},
            ],
        },
        {
            "name": "内容中心",
            "icon": "fas fa-book",
            "models": [
                {"name": "词书管理", "icon": "fas fa-book-open", "url": "/admin/books/book/"},
                {"name": "单词管理", "icon": "fas fa-font", "url": "/admin/books/word/"},
                {"name": "例句管理", "icon": "fas fa-comment-dots", "url": "/admin/books/wordexample/"},
            ],
        },
        {
            "name": "学习计划",
            "icon": "fas fa-calendar-check",
            "models": [
                {"name": "用户计划", "icon": "fas fa-list-check", "url": "/admin/plans/userplan/"},
                {"name": "每日任务", "icon": "fas fa-calendar-day", "url": "/admin/plans/dailytask/"},
            ],
        },
        {
            "name": "学习流程",
            "icon": "fas fa-graduation-cap",
            "models": [
                {"name": "学习记录", "icon": "fas fa-pen", "url": "/admin/learn/learningrecord/"},
                {"name": "单词进度", "icon": "fas fa-signal", "url": "/admin/learn/wordprogress/"},
                {"name": "收藏夹", "icon": "fas fa-heart", "url": "/admin/learn/favorite/"},
                {"name": "复习会话", "icon": "fas fa-redo", "url": "/admin/review/reviewsession/"},
                {"name": "复习记录", "icon": "fas fa-check-double", "url": "/admin/review/reviewrecord/"},
                {"name": "错词本", "icon": "fas fa-exclamation-triangle", "url": "/admin/review/wrongword/"},
            ],
        },
        {
            "name": "AI能力",
            "icon": "fas fa-robot",
            "models": [
                {"name": "AI会话", "icon": "fas fa-comments", "url": "/admin/ai/aiconversation/"},
                {"name": "AI消息", "icon": "fas fa-comment-alt", "url": "/admin/ai/aimessage/"},
                {"name": "AI学习报告", "icon": "fas fa-file-alt", "url": "/admin/ai/aistudyreport/"},
                {"name": "AI反馈", "icon": "fas fa-thumbs-up", "url": "/admin/ai/aiuserfeedback/"},
                {"name": "AI运行日志", "icon": "fas fa-route", "url": "/admin/ai/airequestlog/"},
                {"name": "AI响应缓存", "icon": "fas fa-database", "url": "/admin/ai/airesponsecache/"},
            ],
        },
        {
            "name": "语法学习",
            "icon": "fas fa-language",
            "models": [
                {"name": "语法点", "icon": "fas fa-list", "url": "/admin/grammar/grammarpoint/"},
                {"name": "语法句子", "icon": "fas fa-align-left", "url": "/admin/grammar/grammarsentence/"},
                {"name": "句子标注", "icon": "fas fa-highlighter", "url": "/admin/grammar/grammarannotation/"},
                {"name": "语法学习记录", "icon": "fas fa-clipboard-check", "url": "/admin/grammar/grammarlearningrecord/"},
            ],
        },
        {
            "name": "测试与统计",
            "icon": "fas fa-chart-line",
            "models": [
                {"name": "测试会话", "icon": "fas fa-clipboard-list", "url": "/admin/exams/testsession/"},
                {"name": "测试题目", "icon": "fas fa-question-circle", "url": "/admin/exams/testquestion/"},
                {"name": "测试答案", "icon": "fas fa-check-square", "url": "/admin/exams/testanswer/"},
                {"name": "打卡记录", "icon": "fas fa-calendar-alt", "url": "/admin/stats/checkinrecord/"},
                {"name": "每日统计", "icon": "fas fa-chart-bar", "url": "/admin/stats/studydailystat/"},
            ],
        },
        {
            "name": "系统管理",
            "icon": "fas fa-cogs",
            "models": [
                {"name": "系统配置", "icon": "fas fa-cog", "url": "/admin/system/systemconfig/"},
                {"name": "横幅公告", "icon": "fas fa-bullhorn", "url": "/admin/system/bannernotice/"},
                {"name": "操作日志", "icon": "fas fa-history", "url": "/admin/ops/operationlog/"},
                {"name": "导入任务", "icon": "fas fa-file-import", "url": "/admin/ops/dataimporttask/"},
            ],
        },
    ],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

AI_AGENT_RUNTIME_MODE = os.getenv("AI_AGENT_RUNTIME_MODE", "celery").strip().lower() or "celery"
AI_AGENT_INLINE_RECORDING = os.getenv("AI_AGENT_INLINE_RECORDING", "true").lower() == "true"
AI_AGENT_REQUIRE_APPROVAL_FOR_MUTATIONS = os.getenv("AI_AGENT_REQUIRE_APPROVAL_FOR_MUTATIONS", "true").lower() == "true"
AI_AGENT_QUEUE_SHORT = os.getenv("AI_AGENT_QUEUE_SHORT", "ai_short").strip() or "ai_short"
AI_AGENT_QUEUE_LONG = os.getenv("AI_AGENT_QUEUE_LONG", "ai_long").strip() or "ai_long"
AI_AGENT_QUEUE_TOOLS = os.getenv("AI_AGENT_QUEUE_TOOLS", "ai_tools").strip() or "ai_tools"
AI_AGENT_STALE_QUEUE_SECONDS = int(os.getenv("AI_AGENT_STALE_QUEUE_SECONDS", "30") or 30)
AI_AGENT_STALE_RUNNING_SECONDS = int(os.getenv("AI_AGENT_STALE_RUNNING_SECONDS", "180") or 180)
AI_AGENT_AUTO_RECOVER_ENABLED = os.getenv("AI_AGENT_AUTO_RECOVER_ENABLED", "true").lower() == "true"
AI_AGENT_AUTO_RECOVER_LIMIT = int(os.getenv("AI_AGENT_AUTO_RECOVER_LIMIT", "20") or 20)
AI_AGENT_AUTO_RECOVER_EVERY_SECONDS = int(os.getenv("AI_AGENT_AUTO_RECOVER_EVERY_SECONDS", "60") or 60)

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0").strip() or "redis://127.0.0.1:6379/0"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_DEFAULT_QUEUE = AI_AGENT_QUEUE_SHORT
CELERY_TASK_ROUTES = {
    "apps.ai.tasks.execute_agent_run_task": {"queue": AI_AGENT_QUEUE_LONG},
    "apps.ai.tasks.recover_stale_agent_runs_task": {"queue": AI_AGENT_QUEUE_TOOLS},
}
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
CELERY_TASK_EAGER_PROPAGATES = os.getenv("CELERY_TASK_EAGER_PROPAGATES", "true").lower() == "true"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "ai-agent-recover-stale-runs": {
        "task": "apps.ai.tasks.recover_stale_agent_runs_task",
        "schedule": AI_AGENT_AUTO_RECOVER_EVERY_SECONDS,
        "args": (AI_AGENT_AUTO_RECOVER_LIMIT,),
    }
} if AI_AGENT_AUTO_RECOVER_ENABLED else {}
