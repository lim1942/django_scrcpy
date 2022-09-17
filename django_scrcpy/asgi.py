"""
ASGI config for django_scrcpy project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application
from wserver import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_scrcpy.settings')

django_asgi_app = get_asgi_application()
application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns,
        ),
    ),
    "http": django_asgi_app,
})