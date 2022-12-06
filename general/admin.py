from urllib.parse import quote
from django.urls import reverse
from django.contrib import admin
from django.utils.safestring import mark_safe
from import_export.admin import ExportActionMixin

from general import forms
from general import models
from general import adb


@admin.register(models.Mobile)
class TaskAdmin(ExportActionMixin, admin.ModelAdmin):

    list_per_page = 20
    form = forms.MobileForm
    show_full_result_count = True
    search_fields = ['name']
    list_filter = ['device_type', 'updated_time', 'created_time']
    list_display = ['device_id', 'device_name', 'device_type', 'online', 'screen', 'filemanager', 'updated_time', 'created_time']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['config', 'device_id', 'updated_time', 'created_time']
        else:
            return ['config', 'updated_time', 'created_time']

    def has_add_permission(self, request):
        return False

    def online(self, obj):
        if self.devices_dict.get(obj.device_id):
            return '🟢'
        else:
            return '🔴'
    online.short_description = '在线状态'

    def screen(self, obj):
        query_params = f"?config={quote(obj.config)}"
        mobile_screen_url = reverse("mobile-screen", kwargs={"device_id": obj.device_id, "version": "v1"})
        return mark_safe(f'<a href="{mobile_screen_url}{query_params}" target="_blank">访问</a>')
    screen.short_description = '访问屏幕'

    def filemanager(self, obj):
        mobile_screen_url = reverse("mobile-filemanager", kwargs={"device_id": obj.device_id, "version": "v1"})
        return mark_safe(f'<a href="{mobile_screen_url}" target="_blank">访问</a>')
    filemanager.short_description = '文件管理'

    def changelist_view(self, request, extra_context=None):
        self.devices_dict = adb.AdbDevice.list(slug=True)
        models.Mobile.objects.bulk_create([models.Mobile(device_id=k) for k, v in self.devices_dict.items()], ignore_conflicts=True)
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.config = form.cleaned_data['config']
        obj.save()
