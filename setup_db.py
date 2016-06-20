#!/usr/bin/env python

import os
import sys
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libvirt_dashboard.settings')

django.setup()

from django.db import transaction

from caselink.tasks import update_polarion
from caselink.tasks import update_linkage
from caselink.tasks import update_changes

def run():
    print('Loading polaroin')
    update_polarion()

    print('Loading linkage')
    update_linkage()

    print('Loading changes')
    update_changes()

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    run()
