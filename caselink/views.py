import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.template import RequestContext, loader
from django.forms.models import model_to_dict

from .models import WorkItem, AutoCase, Error
from .serializers import WorkItemSerializer, AutoCaseSerializer
from rest_framework import generics


logger = logging.getLogger('django')


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

            json_case = {}
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
            json_list.append(json_case)

    elif request_type == 'm2a':
        for workitem in WorkItem.objects.all():
            json_case = workitem_to_json(workitem)
            if json_case is None:
                continue
            auto_cases = []
            for caselink in workitem.caselinks.all():
                for case in caselink.autocases.all():
                    auto_cases.append(case)
            json_case['cases'] = [case.id for case in auto_cases]
            json_list.append(json_case)

    return JsonResponse({'data': json_list})
