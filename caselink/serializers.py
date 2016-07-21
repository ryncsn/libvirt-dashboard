from rest_framework import serializers
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist
from .models import *


class LinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink


class WorkItemSerializer(serializers.ModelSerializer):
    caselinks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    bugs = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = WorkItem


class AutoCaseSerializer(serializers.ModelSerializer):
    caselinks = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    failures = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = AutoCase


class WorkItemLinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink
        exclude = ('workitem',)


class BugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bug


class AutoCaseFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoCaseFailure
