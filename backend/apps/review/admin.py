from django.contrib import admin

from .models import ReviewRecord, ReviewSession, WrongWord

admin.site.register(ReviewSession)
admin.site.register(ReviewRecord)
admin.site.register(WrongWord)

# Register your models here.
