#!/usr/bin/env python

import os
import sys
import yaml
import django
import datetime


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libvirt_dashboard.settings')

django.setup()

from django.utils import timezone
from django.db import transaction

from caselink.models import WorkItem, Document
from caselink.tasks import update_linkage
from caselink.tasks import update_polarion

try:
    from builtins import str
except ImportError:
    pass


class literal(str):
    pass


@transaction.atomic
def populate_polarion():
    with open('base_polarion.yaml') as base_fp:
        base = yaml.load(base_fp)

    for wi_id, case in base.items():
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


def run():
    print('Populating baseline polarion cases')
    populate_polarion()

    print('Loading linkage')
    update_linkage()

    print('Loading current polarion cases')
    update_polarion()


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    run()
