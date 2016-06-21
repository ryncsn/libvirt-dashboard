from rest_framework import serializers
from .models import WorkItem, AvocadoCase


class WorkItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkItem

class AvocadoCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvocadoCase

