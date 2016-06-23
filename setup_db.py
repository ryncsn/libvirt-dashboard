#!/usr/bin/env python

import os
import sys
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libvirt_dashboard.settings')

django.setup()

from django.db import transaction

from caselink.tasks import update_error
from caselink.tasks import update_project
from caselink.tasks import update_manualcase
from caselink.tasks import update_autocase_linkage

def run():
    print('Loading Error')
    update_error()

    print('Loading Project')
    update_project()

    print('Loading Manual Cases')
    update_manualcase()

    print('Loading Auto Cases and Linkage')
    update_autocase_linkage()

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    run()
