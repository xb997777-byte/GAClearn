from django.contrib import admin

from .models import DailyTask, PlanRevision, UserPlan

admin.site.register(UserPlan)
admin.site.register(DailyTask)
admin.site.register(PlanRevision)

# Register your models here.
