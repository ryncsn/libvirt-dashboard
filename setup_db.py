#!/usr/bin/env python

import os
import sys
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libvirt_dashboard.settings')

django.setup()

from django.db import transaction

from caselink.tasks import load_error
from caselink.tasks import load_project
from caselink.tasks import load_manualcase
from caselink.tasks import load_autocase_linkage

def run():
    print('Loading Error')
    load_error()

    print('Loading Project')
    load_project()

    print('Loading Manual Cases')
    load_manualcase()

    print('Loading Auto Cases and Linkage')
    load_autocase_linkage()

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    run()
