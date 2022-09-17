from django.urls import path, include
from rest_framework.routers import DefaultRouter
from general import views

router = DefaultRouter()
router.register('worker', views.MobileModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
