import re
import pytz
import base64
import os.path
import datetime
import mimetypes
from wsgiref.util import FileWrapper

from django.urls import reverse
from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.core.files.base import ContentFile
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from general import adb
from general import models
from general import pagination
from general import serializers
from general import permissions
from django_scrcpy.settings import TIME_ZONE, MEDIA_ROOT


class MobileModelViewSet(ReadOnlyModelViewSet):
    lookup_field = 'device_id'
    queryset = models.Mobile.objects.all()
    serializer_class = serializers.MobileModelSerializer
    permission_classes = (permissions.GeneralPermission,)
    pagination_class = pagination.SizePageNumberPagination
    filter_backends = (OrderingFilter, SearchFilter)
    search_fields = ('name',)
    ordering_fields = ('updated_time', 'created_time')
    filemanage_add_timedelta = datetime.datetime.now().astimezone(tz=pytz.timezone(TIME_ZONE)).utcoffset()

    @action(methods=['get'], detail=True, url_path='screen')
    def screen(self, request, *args, **kwargs):
        kwargs['title'] = self.get_object().device_name or kwargs['device_id']
        return render(request, "general/play.html", kwargs)

    @action(methods=['get'], detail=True, url_path='filemanager')
    def filemanager(self, request, *args, **kwargs):
        kwargs['title'] = self.get_object().device_name or kwargs['device_id']
        return render(request, "general/filemanager.html", kwargs)

    @action(methods=['post'], detail=True, url_path='filemanager/list')
    def filemanager_list(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        items = adb_device.filemanager_list(request.data['path'])
        for item in items:
            item['date'] = (item['date'] + self.filemanage_add_timedelta).strftime("%Y-%m-%d %H:%M:%S"),
        return Response({'result': items})

    @action(methods=['post'], detail=True, url_path='filemanager/upload')
    def filemanager_upload(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_upload(request.data['destination'], request._files)
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/rename')
    def filemanager_rename(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_rename(request.data['item'], request.data['newItemPath'])
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/copy')
    def filemanager_copy(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        single_filename = request.data.get('singleFilename', '')
        success, error = adb_device.filemanager_copy(request.data['items'], request.data['newPath'], single_filename=single_filename)
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/move')
    def filemanager_move(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_move(request.data['items'], request.data['newPath'])
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/remove')
    def filemanager_remove(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_remove(request.data['items'])
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/edit')
    def filemanager_edit(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_edit(request.data['item'], request.data['content'].encode('utf-8'))
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/getContent')
    def filemanager_get_content(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        content = adb_device.filemanager_get_content(request.data['item'])
        return Response({"result": content})

    @action(methods=['post'], detail=True, url_path='filemanager/createFolder')
    def filemanager_create_folder(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_create_folder(request.data['newPath'])
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['get'], detail=True, url_path='filemanager/download')
    def filemanager_download(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        iter_content = adb_device.filemanager_iter_content(request.query_params['path'])
        response = StreamingHttpResponse(streaming_content=iter_content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment;filename="%s"' % request.query_params['path']
        return response

    @action(methods=['get'], detail=True, url_path='filemanager/downloadMultiple')
    def filemanager_download_multiple(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        iter_content = adb_device.filemanager_iter_multi_content(request.query_params.getlist('items[]'))
        response = StreamingHttpResponse(streaming_content=iter_content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment;filename="%s"' % os.path.basename(request.query_params['toFilename'])
        return response

    @action(methods=['post'], detail=True, url_path='filemanager/compress')
    def filemanager_compress(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_compress(request.data['items'], request.data['destination'], request.data['compressedFilename'])
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/extract')
    def filemanager_extract(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_extract(request.data['item'], request.data['destination'], request.data['folderName'])
        return Response({"result": {"success": success, "error": error}})

    @action(methods=['post'], detail=True, url_path='filemanager/changePermissions')
    def filemanager_change_permissions(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        success, error = adb_device.filemanager_change_permissions(request.data['items'], request.data['permsCode'], recursive=request.data['recursive'])
        return Response({"result": {"success": success, "error": error}})


class VideoModelViewSet(ModelViewSet):
    lookup_field = 'video_id'
    queryset = models.Video.objects.all()
    serializer_class = serializers.VideoModelSerializer

    @classmethod
    def file_iterator(cls, file_name, chunk_size=8192, offset=0, length=None):
        with open(file_name, "rb") as f:
            f.seek(offset, os.SEEK_SET)
            remaining = length
            while True:
                bytes_length = chunk_size if remaining is None else min(remaining, chunk_size)
                data = f.read(bytes_length)
                if not data:
                    break
                if remaining:
                    remaining -= len(data)
                yield data

    @action(methods=['get'], detail=True, url_path='stream')
    def stream(self, request, *args, **kwargs):
        obj = self.get_object()
        video_path = os.path.join(MEDIA_ROOT, "video", f"{obj.video_id}.{obj.format}")
        range_header = request._request.META.get('HTTP_RANGE', '').strip()
        range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)
        range_match = range_re.match(range_header)
        size = os.path.getsize(video_path)
        content_type, encoding = mimetypes.guess_type(video_path)
        content_type = content_type or 'application/octet-stream'
        if range_match:
            first_byte, last_byte = range_match.groups()
            first_byte = int(first_byte) if first_byte else 0
            last_byte = first_byte + 1024 * 1024 * 8  # 8M 每片,响应体最大体积
            if last_byte >= size:
                last_byte = size - 1
            length = last_byte - first_byte + 1
            resp = StreamingHttpResponse(self.file_iterator(video_path, offset=first_byte, length=length), status=206, content_type=content_type)
            resp['Content-Length'] = str(length)
            resp['Content-Range'] = 'bytes %s-%s/%s' % (first_byte, last_byte, size)
        else:
            resp = StreamingHttpResponse(FileWrapper(open(video_path, 'rb')), content_type=content_type)
            resp['Content-Length'] = str(size)
        resp['Accept-Ranges'] = 'bytes'
        return resp

    @action(methods=['get'], detail=True, url_path='play')
    def play(self, request, *args, **kwargs):
        obj = self.get_object()
        play_url = reverse("video-stream", kwargs={"video_id": obj.video_id, "version": "v1"})
        kwargs = {"filename": f"{obj.video_id}.{obj.format}", "play_url": play_url}
        return render(request, "general/video_play.html", kwargs)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class PictureModelViewSet(ModelViewSet):
    queryset = models.Picture.objects.all()
    serializer_class = serializers.PictureModelSerializer
    authentication_classes = (BasicAuthentication, CsrfExemptSessionAuthentication)

    @action(methods=['post'], detail=False, url_path='upload_base64')
    def upload_base64(self, request, *args, **kwargs):
        base64_data = base64.b64decode(request.data['img'].split('data:image/png;base64,')[-1])
        picture = ContentFile(base64_data, name=request.data['device_id']+'.jpg')
        models.Picture.objects.create(device_id=request.data['device_id'], picture=picture)
        return Response("{\"status\":\"true\"}")
