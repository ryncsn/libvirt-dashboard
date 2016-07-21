import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.http import Http404
from django.template import RequestContext, loader
from django.forms.models import model_to_dict
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, OperationalError, transaction

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from.tasks import *
from .models import *
from .serializers import *

from celery.task.control import inspect
from celery.result import AsyncResult


# Standard RESTful APIs

class WorkItemList(generics.ListCreateAPIView):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.error_check(depth=1)


class WorkItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.error_check(depth=1)

    def perform_destroy(self, instance):
        related = instance.get_related()
        instance.delete()
        for item in related:
            item.error_check(depth=0)


class AutoCaseList(generics.ListCreateAPIView):
    queryset = AutoCase.objects.all()
    serializer_class = AutoCaseSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        # TODO: ignored autolink list
        instance.autolink()
        instance.error_check(depth=1)


class AutoCaseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AutoCase.objects.all()
    serializer_class = AutoCaseSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.autolink()
        instance.error_check(depth=1)

    def perform_destroy(self, instance):
        related = instance.get_related()
        instance.delete()
        for item in related:
            item.error_check(depth=0)

class LinkageList(generics.ListCreateAPIView):
    queryset = CaseLink.objects.all()
    serializer_class = LinkageSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.autolink()
        instance.error_check(depth=1)


class LinkageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = CaseLink.objects.all()
    serializer_class = LinkageSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.autolink()
        instance.error_check(depth=1)

    def perform_destroy(self, instance):
        related = instance.get_related()
        instance.delete()
        for item in related:
            item.error_check(depth=0)


class BugList(generics.ListCreateAPIView):
    queryset = Bug.objects.all()
    serializer_class = BugSerializer


class BugDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bug.objects.all()
    serializer_class = BugSerializer


class AutoCaseFailureList(generics.ListCreateAPIView):
    queryset = AutoCaseFailure.objects.all()
    serializer_class = AutoCaseFailureSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.autolink()
        #instance.error_check(depth=1)


class AutoCaseFailureDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AutoCaseFailure.objects.all()
    serializer_class = AutoCaseFailureSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.autolink()
        #instance.error_check(depth=1)

    def perform_destroy(self, instance):
        #related = instance.get_related()
        instance.delete()
        #for item in related:
        #    item.error_check(depth=0)


class BugList(generics.ListCreateAPIView):
    queryset = Bug.objects.all()
    serializer_class = BugSerializer


class BugDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bug.objects.all()
    serializer_class = BugSerializer


# Shortcuts RESTful APIs

class WorkItemLinkageList(APIView):
    """
    Retrieve, update or delete a caselink instance of a workitem.
    """

    # This serializer is only used for html view to hide workitem field
    serializer_class = WorkItemLinkageSerializer

    def get_objects(self, workitem):
        wi = get_object_or_404(WorkItem, id=workitem)
        try:
            return CaseLink.objects.filter(workitem=wi)
        except CaseLink.DoesNotExist:
            raise Http404

    def get(self, request, workitem, format=None):
        caselinks = self.get_objects(workitem)
        serializers = [LinkageSerializer(caselink) for caselink in caselinks]
        return Response(serializer.data for serializer in serializers)

    def post(self, request, workitem, format=None):
        request.data['workitem'] = workitem
        serializer = LinkageSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            instance.autolink()
            instance.error_check(depth=1)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkItemLinkageDetail(APIView):
    """
    Retrieve, update or delete a caselink instance of a workitem.
    """

    serializer_class = WorkItemLinkageSerializer

    def get_object(self, workitem, pattern):
        wi = get_object_or_404(WorkItem, id=workitem)
        try:
            return CaseLink.objects.get(workitem=wi, autocase_pattern=pattern)
        except CaseLink.DoesNotExist:
            raise Http404

    def get(self, request, workitem, pattern, format=None):
        caselink = self.get_object(workitem, pattern)
        serializer = LinkageSerializer(caselink)
        return Response(serializer.data)

    def put(self, request, workitem, pattern, format=None):
        request.data['workitem'] = workitem
        caselink = self.get_object(workitem, pattern)
        serializer = LinkageSerializer(caselink, data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            instance.autolink()
            instance.error_check(depth=1)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, workitem, pattern, format=None):
        caselink = self.get_object(workitem, pattern)
        related = caselink.get_related()
        caselink.delete()
        for item in related:
            item.error_check(depth=0)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutoCaseLinkageList(APIView):
    """
    Retrieve, update or delete a caselink instance of a autocase.
    """

    serializer_class = LinkageSerializer

    def get_objects(self, autocase):
        case = get_object_or_404(AutoCase, id=autocase)
        try:
            return case.caselinks.all();
        except CaseLink.DoesNotExist:
            raise Http404

    def get(self, request, autocase, format=None):
        caselinks = self.get_objects(autocase)
        serializers = [LinkageSerializer(caselink) for caselink in caselinks]
        return Response(serializer.data for serializer in serializers)


def a2m(request):
    template = loader.get_template('caselink/a2m.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def m2a(request):
    template = loader.get_template('caselink/m2a.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def index(request):
    template = loader.get_template('caselink/index.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def task_control(request):

    operations = []
    task_to_trigger = request.GET.getlist('trigger', [])

    if 'linkage_error_check' in task_to_trigger:
        operations.append(update_linkage_error)
    if 'autocase_error_check' in task_to_trigger:
        operations.append(update_autocase_error)
    if 'manualcase_error_check' in task_to_trigger:
        operations.append(update_manualcase_error)

    async = True if request.GET.get('async', '') == 'true' else False

    if len(operations) > 0:
        if not async:
            try:
                for op in operations:
                    with transaction.atomic():
                        op()
            except OperationalError:
                return JsonResponse({'message': 'DB Locked'})
            except IntegrityError:
                return JsonResponse({'message': 'Integrity Check Failed'})
            return JsonResponse({'message': 'done'})
        else:
            for op in operations:
                op.apply_async()
            return JsonResponse({'message': 'queued'})

    workers = inspect()
    task_status = {}
    for worker, tasks in workers.active().items():
        for task in tasks:
            res = AsyncResult(task['id'])
            task_status[task['name']] = {
                'state': res.state,
                'meta': res.info
            }
    return JsonResponse(task_status)


def data(request):
    request_type = request.GET.get('type', 'm2a')

    def workitem_to_json(workitem):
        if workitem.type == 'heading':
            return None
        json_case = model_to_dict(workitem)
        json_case['polarion'] = workitem.id
        json_case['documents'] = [doc.id for doc in workitem.documents.all()]
        json_case['errors'] = [error.message for error in workitem.errors.all()]
        return json_case

    json_list = []

    if request_type == 'a2m':
        for auto_case in AutoCase.objects.all():
            workitems = []
            for caselink in auto_case.caselinks.all():
                workitems.append(caselink.workitem)

            json_case = {
                "errors": [],
                "polarion": [],
                "title": [],
                "automation": [],
                "project": [],
                "documents": [],
                "commit": [],
                "type": [],
                "id": [],
                "archs": []
            }

            for workitem in workitems:
                item_case = workitem_to_json(workitem)
                if item_case is None:
                    continue
                for key in item_case:
                    if key == 'errors':
                        continue
                    try:
                        json_case[key].append(item_case[key])
                    except KeyError:
                        json_case[key] = [item_case[key]];

            json_case['case'] = auto_case.id
            json_case['errors'].append([err.message for err in auto_case.errors.all()])
            json_list.append(json_case)

    elif request_type == 'm2a':
        for workitem in WorkItem.objects.all():
            json_case = workitem_to_json(workitem)
            if json_case is None:
                continue
            auto_cases = []
            json_case['patterns'] = []
            try:
                caselinks = workitem.caselinks.all()
                for case in caselinks:
                    json_case['errors'] += [err.message for err in case.errors.all()]
                    json_case['patterns'].append(case.autocase_pattern)
                    for auto_case in case.autocases.all():
                        auto_cases.append(auto_case)
            except ObjectDoesNotExist:
                pass
            json_case['cases'] = [case.id for case in auto_cases]
            json_list.append(json_case)

    return JsonResponse({'data': json_list})
