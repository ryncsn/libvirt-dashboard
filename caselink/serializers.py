from rest_framework import serializers
from .models import WorkItem, AutoCase, CaseLink, Bug, BugPattern
from django.utils.translation import ugettext as _
from django.core.exceptions import ObjectDoesNotExist


class LinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink


class WorkItemSerializer(serializers.ModelSerializer):
    caselinks = LinkageSerializer(many=True, read_only=True)
    class Meta:
        model = WorkItem


class AutoCaseSerializer(serializers.ModelSerializer):
    caselinks = LinkageSerializer(many=True, read_only=True)
    class Meta:
        model = AutoCase


class WorkItemLinkageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseLink
        exclude = ('workitem',)

class SlugAutoCreateRelatedField(serializers.RelatedField):
    """
    Always return a new created unsaved instance
    """

    default_error_messages = {
        'does_not_exist': _('Object with {slug_name}={value} does not exist.'),
        'invalid': _('Invalid value.'),
    }

    def __init__(self, slug_field=None, **kwargs):
        assert slug_field is not None, 'The `slug_field` argument is required.'
        self.slug_field = slug_field
        super(SlugAutoCreateRelatedField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            value = self.get_queryset().model(**{self.slug_field: data})
        except (TypeError, ValueError):
            self.fail('invalid')
        return value

    def to_representation(self, obj):
        return getattr(obj, self.slug_field)


class BugSerializer(serializers.ModelSerializer):
    autocase_patterns = SlugAutoCreateRelatedField(queryset=BugPattern.objects.all(), slug_field='autocase_pattern', many=True)

    class Meta:
        model = Bug
        fields = ('id', 'autocases', 'workitems', 'autocase_patterns',)

    def create(self, validated_data):
        bug = Bug.objects.create(id=validated_data['id'])
        for wi in validated_data['workitems']:
            bug.workitems.add(wi)
        for case in validated_data['autocases']:
            bug.autocases.add(case)
        for pattern in validated_data['autocase_patterns']:
            pattern.bug = bug
            pattern.save()
        return bug

    def update(self, bug, validated_data):
        bug.id = validated_data.get('id', bug.id)
        bug.workitems.clear()
        bug.autocases.clear()
        bug.autocase_patterns.all().delete()
        for wi in validated_data['workitems']:
            bug.workitems.add(wi)
        for case in validated_data['autocases']:
            bug.autocases.add(case)
        for pattern in validated_data['autocase_patterns']:
            pattern.bug = bug
            pattern.save()
        return bug
