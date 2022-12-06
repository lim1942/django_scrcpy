import os.path
from django.shortcuts import render
from django.http import StreamingHttpResponse
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from general import models
from general import pagination
from general import serializers
from general import permissions
from general import adb


class MobileModelViewSet(ReadOnlyModelViewSet):
    lookup_field = 'device_id'
    queryset = models.Mobile.objects.all()
    serializer_class = serializers.MobileModelSerializer
    permission_classes = (permissions.TaskPermission,)
    pagination_class = pagination.SizePageNumberPagination
    filter_backends = (OrderingFilter, SearchFilter)
    search_fields = ('name',)
    ordering_fields = ('updated_time', 'created_time')

    @action(methods=['get'], detail=True, url_path='screen')
    def screen(self, request, *args, **kwargs):
        kwargs['title'] = self.get_object().device_name or kwargs['device_id']
        return render(request, "general/play.html", kwargs)

    @action(methods=['get'], detail=True, url_path='filemanager')
    def filemanager(self, request, *args, **kwargs):
        kwargs['title'] = self.get_object().device_name or kwargs['device_id']
        print(kwargs)
        return render(request, "general/filemanager.html", kwargs)

    @action(methods=['post'], detail=True, url_path='filemanager/list')
    def filemanager_list(self, request, *args, **kwargs):
        adb_device = adb.AdbDevice(kwargs['device_id'])
        return Response({'result': adb_device.filemanager_list(request.data['path'])})

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
