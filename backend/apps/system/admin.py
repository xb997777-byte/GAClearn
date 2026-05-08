from django.contrib import admin

from .models import BannerNotice, SystemConfig

admin.site.register(SystemConfig)
admin.site.register(BannerNotice)

# Register your models here.
