from django.contrib import admin

from .models import TestAnswer, TestQuestion, TestSession

admin.site.register(TestSession)
admin.site.register(TestQuestion)
admin.site.register(TestAnswer)

# Register your models here.
