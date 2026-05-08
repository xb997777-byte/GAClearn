from django.contrib import admin

from .models import DataImportTask, OperationLog

admin.site.register(OperationLog)
admin.site.register(DataImportTask)

# Register your models here.
