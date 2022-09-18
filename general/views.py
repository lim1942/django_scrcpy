from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import OrderingFilter, SearchFilter

from general import models
from general import pagination
from general import serializers
from general import permissions


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
        return render(request, "play.html", kwargs)
