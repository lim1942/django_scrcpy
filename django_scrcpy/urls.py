"""django_scrcpy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.views.static import serve
from django.urls import path, re_path, include
from django_scrcpy.settings import STATIC_ROOT, MEDIA_ROOT

admin.site.site_header = 'django_scrcpy'
admin.site.site_title = 'django_scrcpy'
admin.site.index_title = 'django_scrcpy'

urlpatterns = [
    re_path('^static/(?P<path>.*)$', serve, {'document_root': STATIC_ROOT}),
    re_path('^media/(?P<path>.*)$', serve, {'document_root': MEDIA_ROOT}),
    path('api/<str:version>/general/', include('general.urls')),
    path('asynch/', include('asynch.urls')),
    path('admin/', admin.site.urls),
]
