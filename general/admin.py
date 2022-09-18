from django.urls import reverse
from django.contrib import admin
from django.utils.safestring import mark_safe
from import_export.admin import ExportActionMixin

from general import models
from general import forms


@admin.register(models.Mobile)
class TaskAdmin(ExportActionMixin, admin.ModelAdmin):
    list_per_page = 20
    form = forms.MobileForm
    show_full_result_count = True
    search_fields = ['name']
    list_filter = ['device_type', 'updated_time', 'created_time']
    list_display = ['device_id', 'device_name', 'device_type', 'process', 'online', 'screen', 'updated_time', 'created_time']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['device_id', 'updated_time', 'created_time']
        else:
            return ['updated_time', 'created_time']

    def has_add_permission(self, request):
        return False

    def process(self, obj):
        return '-'
    process.short_description = '进程号'

    def online(self, obj):
        return '🔴'
        # return '🟢'
    online.short_description = '在线状态'

    def screen(self, obj):
        mobile_screen_url = reverse("mobile-screen", kwargs={"device_id": obj.device_id, "version": "v1"})
        return mark_safe(f'<a href="{mobile_screen_url}" target="_blank">访问</a>')
    screen.short_description = '访问屏幕'
