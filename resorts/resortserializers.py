from rest_framework import serializers
from resorts.models import resortItem


class ResortItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = resortItem
        fields = "__all__"
