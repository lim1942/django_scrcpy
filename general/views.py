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
    ordering_fields = ('online', 'updated_time', 'created_time')

