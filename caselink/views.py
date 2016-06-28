import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.http import Http404
from django.template import RequestContext, loader
from django.forms.models import model_to_dict
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from .models import WorkItem, AutoCase, CaseLink, Error
from .serializers import \
        WorkItemSerializer, AutoCaseSerializer, LinkageSerializer, WorkItemLinkageSerializer
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class WorkItemList(generics.ListCreateAPIView):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer


class WorkItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer


class AutoCaseList(generics.ListCreateAPIView):
    queryset = AutoCase.objects.all()
    serializer_class = AutoCaseSerializer


class AutoCaseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AutoCase.objects.all()
    serializer_class = AutoCaseSerializer


class LinkageList(generics.ListCreateAPIView):
    queryset = CaseLink.objects.all()
    serializer_class = LinkageSerializer


class LinkageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = CaseLink.objects.all()
    serializer_class = LinkageSerializer


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
            serializer.save()
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
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, workitem, pattern, format=None):
        caselink = self.get_object(workitem, pattern)
        caselink.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def a2m(request):
    template = loader.get_template('caselink/a2m.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def index(request):
    template = loader.get_template('caselink/index.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


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
            try:
                caselinks = workitem.caselinks.all()
                for case in caselinks:
                    for auto_case in case.autocases.all():
                        auto_cases.append(auto_case)
            except ObjectDoesNotExist:
                pass
            json_case['cases'] = [case.id for case in auto_cases]
            json_list.append(json_case)

    return JsonResponse({'data': json_list})
