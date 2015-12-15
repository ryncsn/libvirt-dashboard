import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.template import RequestContext, loader
from django.forms.models import model_to_dict

from .models import WorkItem, Error
from .tasks import create_jira_issue


logger = logging.getLogger('django')


def index(request):
    template = loader.get_template('caselink/index.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


def update(request):
    wi_id = request.POST.get('id')
    response = {'job': wi_id}

    create_jira_issue.delay(wi_id)

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
    json_list = []
    for workitem in WorkItem.objects.all():
        if workitem.type == 'heading':
            continue
        json_case = model_to_dict(workitem)
        json_case['polarion'] = workitem.wi_id
        json_case['tcms'] = ','.join(
            [case.tcmsid for case in workitem.tcmscase_set.all()])
        json_case['documents'] = '<br/>'.join(
            [doc.doc_id for doc in workitem.document_set.all()])
        json_case['cases'] = '<br/>'.join(
            [case.name for case in workitem.avocadocase_set.all()])
        json_case['errors'] = '<br/>'.join(
            [error.name for error in workitem.errors.all()]
        )
        json_case['diffs'] = '<br/>'.join(
            [change.diff for change in workitem.change_set.all()])
        json_case['changes'] = ''
        json_list.append(json_case)

    return JsonResponse({'data': json_list})
