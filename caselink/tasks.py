import yaml
import re
import logging
import difflib
import datetime

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from celery import shared_task

# pylint: disable=redefined-builtin
try:
    from builtins import str
except ImportError:
    pass

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

from caselink.models import WorkItem, Document, Change
from caselink.models import AvocadoCase, TCMSCase, Error


def update_polarion():
    _update_polarion_db(_load_polarion())


def update_linkage():
    _update_linkage_db(_load_linkage())


def _load_polarion():
    with open('base_polarion.yaml') as polarion_fp:
        polarion = yaml.load(polarion_fp)
    return polarion


def _load_linkage():
    with open('autotest_cases.yaml') as linkage_fp:
        linkage = yaml.load(linkage_fp)
    return linkage


def _load_updates():
    with open('updates.yaml') as updates_fp:
        updates = yaml.load(updates_fp)
    changes = {k: v['changes'] for k, v in updates.items() if 'changes' in v}
    return changes


@transaction.atomic
def _update_polarion_db(polarion):
    for wi_id, case in polarion.items():
        # pylint: disable=no-member
        workitem, _ = WorkItem.objects.get_or_create(wi_id=wi_id)
        workitem.title = case['title']
        workitem.type = case['type']
        updated = timezone.make_aware(
            case['updated'] - datetime.timedelta(hours=8))
        workitem.updated = workitem.confirmed = updated
        workitem.save()

        for doc_id in case['documents']:
            doc, _ = Document.objects.get_or_create(doc_id=doc_id)
            doc.workitems.add(workitem)
            doc.save()


@transaction.atomic
def _update_linkage_db(linkage):
    # pylint: disable=no-member
    multiple_polarion_error, _ = Error.objects.get_or_create(
        name='More than one polarion for one auto case')

    for link in linkage:
        wis = []
        wi_ids = link.get('polarion', {}).keys()
        case_names = link.get('cases', [])
        tcms_ids = link.get('tcms', {}).keys()
        automated = link.get('automated', True)
        comment = link.get('comment', '')
        feature = link.get('feature', '')

        # Log error when wi_ids is not unique.
        # Will remove this when cases are cleaned up.
        if not wi_ids:
            logging.error("No Polarion specified in linkage for %s",
                          link.get('title', ''))
        elif len(wi_ids) > 1:
            logging.error("More than one polarion for one linkage for %s: %s",
                          link.get('title', ''), wi_ids)

        for wi_id in wi_ids:
            try:
                wi = WorkItem.objects.get(wi_id=wi_id)
            except ObjectDoesNotExist:
                logging.error("Work Item %s in linkage not found on Polarion",
                              wi_id)
                continue

            if len(wi_ids) > 1:
                wi.errors.add(multiple_polarion_error)

            if automated:
                wi.automation = 'automated'
            else:
                if comment:
                    wi.comment = comment
                    wi.automation = 'manualonly'
                else:
                    wi.automation = 'updating'
            wi.feature = feature
            wi.save()
            wis.append(wi)

        for tcmsid in tcms_ids:
            case, _ = TCMSCase.objects.get_or_create(tcmsid=tcmsid)
            for wi in wis:
                case.workitems.add(wi)
            case.save()

        for name in case_names:
            case, _ = AvocadoCase.objects.get_or_create(name=name)
            for wi in wis:
                case.workitems.add(wi)
            case.save()
