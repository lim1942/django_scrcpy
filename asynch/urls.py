from django.urls import path

from asynch.ws import DeviceWebsocketConsumer
from asynch.view import api


websocket_urlpatterns = [
    path("stream/device/<str:device_id>/", DeviceWebsocketConsumer.as_asgi()),
]

urlpatterns = [
    path("", api.urls),
]
