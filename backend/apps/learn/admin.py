from django.contrib import admin

from .models import Favorite, LearningRecord, WordProgress

admin.site.register(LearningRecord)
admin.site.register(WordProgress)
admin.site.register(Favorite)

# Register your models here.
