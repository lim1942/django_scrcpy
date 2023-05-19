from rest_framework import serializers
from general import models


class MobileModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Mobile
        fields = '__all__'


class VideoModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Video
        fields = '__all__'


class PictureModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Picture
        fields = '__all__'
