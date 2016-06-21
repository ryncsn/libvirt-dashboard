import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.template import RequestContext, loader
from django.forms.models import model_to_dict

from .models import WorkItem, AvocadoCase, Error
from .serializers import WorkItemSerializer, AvocadoCaseSerializer
from rest_framework import generics


logger = logging.getLogger('django')


class WorkItemList(generics.ListCreateAPIView):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer


class WorkItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorkItem.objects.all()
    serializer_class = WorkItemSerializer


class AvocadoCaseList(generics.ListCreateAPIView):
    queryset = AvocadoCase.objects.all()
    serializer_class = AvocadoCaseSerializer


class AvocadoCaseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AvocadoCase.objects.all()
    serializer_class = AvocadoCaseSerializer



def a2m(request):
    template = loader.get_template('caselink/a2m.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def index(request):
    template = loader.get_template('caselink/index.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def update(request):
    wi_id = request.POST.get('id')
    response = {'job': wi_id}

    # Confirm change
    wi = WorkItem.objects.get(wi_id=wi_id)
    wi.confirmed = wi.updated
    changed_error, _ = Error.objects.get_or_create(
        name='Updates not confirmed')
    wi.errors.remove(changed_error)
    return JsonResponse(response)


def ignore(request):
    wi_id = request.POST.get('id')
    response = {'job': wi_id}

    # Confirm change
    wi = WorkItem.objects.get(wi_id=wi_id)
    wi.confirmed = wi.updated
    changed_error, _ = Error.objects.get_or_create(
        name='Updates not confirmed')
    wi.errors.remove(changed_error)
    return JsonResponse(response)


def data(request):
    request_type = request.GET.get('type', 'm2a')

    def workitem_to_json(workitem):
        if workitem.type == 'heading':
            return None
        json_case = model_to_dict(workitem)
        json_case['polarion'] = workitem.wi_id
        json_case['tcms'] = ','.join(
            [case.tcmsid for case in workitem.tcmscase_set.all()])
        json_case['documents'] = '<br/>'.join(
            [doc.doc_id for doc in workitem.document_set.all()])
        json_case['errors'] = '<br/>'.join(
            [error.name for error in workitem.errors.all()])
        json_case['diffs'] = '<br/>'.join(
            [change.diff for change in workitem.change_set.all()])
        json_case['changes'] = ''
        return json_case

    json_list = []

    if request_type == 'a2m':
        for avocado_case in AvocadoCase.objects.all():
            workitems = avocado_case.workitems.all()

            if len(workitems) == 0:
                logger.error("Auto case:" + str(avocado_case.name) + "is not linked")
                continue

            if len(avocado_case.name) == 0:
                logger.info("Auto with no name founded")
                avocado_case.name = "NONAME"
                continue

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

            json_case['case'] = avocado_case.name
            json_list.append(json_case)

    elif request_type == 'm2a':
        for workitem in WorkItem.objects.all():
            json_case = workitem_to_json(workitem)
            if json_case is None:
                continue
            json_case['cases'] = '<br/>'.join(
                [case.name for case in workitem.avocadocase_set.all()])
            json_list.append(json_case)

    return JsonResponse({'data': json_list})
