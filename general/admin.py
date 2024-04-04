import os
import json
import time
from typing import Any, Optional
from urllib.parse import quote
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.urls import reverse
from django.contrib import admin
from django.utils.safestring import mark_safe
from import_export.admin import ExportActionMixin

from general import forms
from general import models
from general import adb
from django_scrcpy.settings import MEDIA_ROOT


@admin.register(models.Mobile)
class MobileAdmin(ExportActionMixin, admin.ModelAdmin):
    save_on_top = True
    list_per_page = 20
    form = forms.MobileForm
    show_full_result_count = True
    search_fields = ['name']
    list_filter = ['device_type', 'user', 'updated_time', 'created_time']
    list_display = ['device_id', 'device_name', 'user', 'device_type', 'recorder', 'online', 'screen', 'filemanager', 'updated_time', 'created_time']
    actions = ['connect', 'disconnect', 'tcpip5555']

    def connect(self, request, queryset):
        for obj in queryset:
            adb.AdbDevice.connect(obj.device_id)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser and 'user' in fields:
            fields.remove('user')
        return fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        else:
            return queryset.filter(user=request.user)

    def disconnect(self, request, queryset):
        for obj in queryset:
            adb.AdbDevice.disconnect(obj.device_id)

    def tcpip5555(self, request, queryset):
        for obj in queryset:
            adb.AdbDevice.tcpip(obj.device_id)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['config', 'device_id', 'updated_time', 'created_time']
        else:
            return ['config', 'updated_time', 'created_time']

    def has_add_permission(self, request):
        return False
    
    def recorder(self, obj):
        if json.loads(obj.config).get('recorder_enable'):
            return '🟢'
        else:
            return '🔴'
    recorder.short_description = '开启录屏'

    def online(self, obj):
        if self.devices_dict.get(obj.device_id, {}).get('online'):
            return '🟢'
        else:
            return '🔴'
    online.short_description = '在线状态'

    def screen(self, obj):
        if self.devices_dict.get(obj.device_id, {}).get('online'):
            query_params = f"?config={quote(obj.config)}"
            mobile_screen_url = reverse("mobile-screen", kwargs={"device_id": obj.device_id, "version": "v1"})
            return mark_safe(f'<a href="{mobile_screen_url}{query_params}" target="_blank">访问</a>')
    screen.short_description = '访问屏幕'

    def filemanager(self, obj):
        if self.devices_dict.get(obj.device_id, {}).get('online'):
            mobile_filemanager_url = reverse("mobile-filemanager", kwargs={"device_id": obj.device_id, "version": "v1"})
            return mark_safe(f'<a href="{mobile_filemanager_url}" target="_blank">访问</a>')
    filemanager.short_description = '文件管理'

    def changelist_view(self, request, extra_context=None):
        self.devices_dict = adb.AdbDevice.list(slug=True)
        models.Mobile.objects.bulk_create([models.Mobile(device_id=v['device_id'], device_type=v['marketname'])
                                           for v in self.devices_dict.values()], ignore_conflicts=True)
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.config = form.cleaned_data['config']
        obj.save()


@admin.register(models.Video)
class VideoAdmin(ExportActionMixin, admin.ModelAdmin):
    list_per_page = 20
    show_full_result_count = True
    search_fields = ['device_id']
    list_filter = ['device_id', 'format', 'start_time', 'finish_time']
    list_display = ['video_id', 'format', 'device_id', 'name', 'duration', 'size', 'video_play', 'start_time', 'finish_time']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['video_id', 'device_id', 'format', 'start_time', 'finish_time', 'config', 'duration']
        else:
            return []

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        for obj in queryset:
            video_path = os.path.join(MEDIA_ROOT, 'video', f'{obj.video_id}.{obj.format}')
            try:
                os.remove(video_path)
            except:
                pass
        return super().delete_queryset(request, queryset)
    
    def delete_model(self, request: HttpRequest, obj: Any) -> None:
        video_path = os.path.join(MEDIA_ROOT, 'video', f'{obj.video_id}.{obj.format}')
        try:
            os.remove(video_path)
        except:
            pass
        return super().delete_model(request, obj)

    def download(self, obj):
        download_url = f'/media/video/{obj.video_id}.{obj.format}'
        download_name = f'{obj.video_id}.{obj.format}'
        return mark_safe(f'<a href="{download_url}" target="_blank" download="{download_name}">访问</a>')
    download.short_description = '下载'

    def video_play(self, obj):
        filename = f"{obj.video_id}.{obj.format}"
        video_play_url = reverse("asynch:video-play") + f"?filename={filename}"
        return mark_safe(f'<a href="{video_play_url}" target="_blank">访问</a>')
    video_play.short_description = '播放/下载'


@admin.register(models.Picture)
class PictureAdmin(ExportActionMixin, admin.ModelAdmin):
    list_per_page = 20
    show_full_result_count = True
    search_fields = ['device_id']
    list_filter = ['device_id', 'created_time']
    list_display = ['img', 'name', 'device_id', 'download', 'created_time']

    def download(self, obj):
        download_url = obj.picture.url
        return mark_safe(f'<a href="{download_url}" download="{obj.device_id}.jpg">访问</a>')
    download.short_description = '下载'

    def img(self, obj):
        return mark_safe(f'<img src="{obj.picture.url}" height="100" width="100">')
    img.short_description = '截图'

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        for obj in queryset:
            picture_path = os.path.join(MEDIA_ROOT, 'picture', obj.picture.url.split('/')[-1])
            try:
                os.remove(picture_path)
            except:
                pass
        return super().delete_queryset(request, queryset)
    
    def delete_model(self, request: HttpRequest, obj: Any) -> None:
        picture_path = os.path.join(MEDIA_ROOT, 'picture', obj.picture.url.split('/')[-1])
        try:
            os.remove(picture_path)
        except:
            pass
        return super().delete_model(request, obj)
