from django.urls import path, include
from rest_framework.routers import DefaultRouter
from general import views

router = DefaultRouter()
router.register('mobile', views.MobileModelViewSet)
router.register('video', views.VideoModelViewSet)
router.register('picture', views.PictureModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
