from django.urls import path

from wserver.consumer import LocalConsumer, VideoConsumer, ControlConsumer


websocket_urlpatterns = [
    path("stream/local/", LocalConsumer.as_asgi()),
    path("stream/video/", VideoConsumer.as_asgi()),
    path("stream/control/", ControlConsumer.as_asgi()),
]