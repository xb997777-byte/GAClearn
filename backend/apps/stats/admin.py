from django.contrib import admin

from .models import CheckinRecord, StudyDailyStat

admin.site.register(CheckinRecord)
admin.site.register(StudyDailyStat)

# Register your models here.
