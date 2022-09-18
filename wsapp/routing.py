from django.urls import path

from wsapp.handles import LocalWsHandle, VideoWsHandle, ControlWsHandle


websocket_urlpatterns = [
    path("stream/local/<str:device_id>/", LocalWsHandle),
    path("stream/video/<str:device_id>/", VideoWsHandle),
    path("stream/control/<str:device_id>/", ControlWsHandle),
]