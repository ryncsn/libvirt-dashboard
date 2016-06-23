from rest_framework import serializers
from .models import WorkItem, AutoCase, CaseLink


class WorkItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkItem

class AutoCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoCase

class LinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink

