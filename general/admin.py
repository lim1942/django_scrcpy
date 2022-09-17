from django.contrib import admin
from import_export.admin import ExportActionMixin

from general import models
from general import forms


@admin.register(models.Mobile)
class TaskAdmin(ExportActionMixin, admin.ModelAdmin):
    list_per_page = 20
    form = forms.MobileForm
    show_full_result_count = True
    search_fields = ['name']
    list_filter = ['device_type', 'online', 'updated_time', 'created_time']
    list_display = ['device_id', 'device_name', 'device_type', 'online', 'updated_time', 'created_time']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['device_id', 'online', 'updated_time', 'created_time']
        else:
            return ['updated_time', 'created_time']

    def has_add_permission(self, request):
        return False

