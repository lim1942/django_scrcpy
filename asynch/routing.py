from django.urls import path

from asynch.ws import DeviceWebsocketConsumer


websocket_urlpatterns = [
    path("stream/device/<str:device_id>/", DeviceWebsocketConsumer.as_asgi()),
]
