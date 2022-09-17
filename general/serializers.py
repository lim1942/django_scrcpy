from rest_framework import serializers
from general import models


class MobileModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Mobile
        fields = '__all__'
