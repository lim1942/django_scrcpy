from django.urls import path

from wserver.consumer import LocalConsumer, VideoConsumer, ControlConsumer


websocket_urlpatterns = [
    path("stream/local/<str:device_id>/", LocalConsumer.as_asgi()),
    path("stream/video/<str:device_id>/", VideoConsumer.as_asgi()),
    path("stream/control/<str:device_id>/", ControlConsumer.as_asgi()),
]