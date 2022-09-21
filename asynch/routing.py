from django.urls import path

from asynch.asyncws import VideoWebsocketConsumer


websocket_urlpatterns = [
    path("stream/video/<str:device_id>/", VideoWebsocketConsumer.as_asgi()),
]
