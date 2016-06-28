from rest_framework import serializers
from .models import WorkItem, AutoCase, CaseLink

class LinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink

class WorkItemLinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink
        exclude = ('workitem',)

class WorkItemSerializer(serializers.ModelSerializer):
    caselinks = LinkageSerializer(many=True, read_only=True)
    class Meta:
        model = WorkItem

class AutoCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoCase

