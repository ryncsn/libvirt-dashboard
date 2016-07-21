from __future__ import absolute_import

import yaml
import re
import logging
import difflib
import datetime

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from celery import shared_task, current_task

# pylint: disable=redefined-builtin
try:
    from builtins import str
except ImportError:
    pass

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

from caselink.models import *


@transaction.atomic
def load_error():
    """Load baseline Error"""
    _load_error_db(_baseline_loader('base_error.yaml'))


@transaction.atomic
def load_project():
    """Load baseline Project"""
    _load_project_db(_baseline_loader('base_project.yaml'))


@transaction.atomic
def load_manualcase():
    """Load baseline Manual cases"""
    _load_manualcase_db(_baseline_loader('base_workitem.yaml'))


@transaction.atomic
def load_linkage():
    """Load baseline linkage"""
    _load_libvirt_ci_linkage_db(_baseline_loader('base_libvirt_ci_linkage.yaml'))


@transaction.atomic
def load_autocase():
    """Load baseline Auto cases"""
    _load_libvirt_ci_autocase_db(_baseline_loader('base_libvirt_ci_autocase.yaml'))


@transaction.atomic
def load_autocase_failure():
    """Load baseline Auto cases"""
    _load_failure_and_bug(_baseline_loader('base_buglist.yaml'))


@transaction.atomic
def init_error_checking():
    """Load baseline Auto cases"""
    update_manualcase_error()
    update_autocase_error()
    update_linkage_error()


@shared_task
def update_linkage_error(link=None):
    """Check for errors in linkage"""
    if not link:
        links = CaseLink.objects.all()
    else:
        links = [link]

    current = 0
    total = len(links)
    direct_call = current_task.request.id is None

    for link in links:
        link.error_check(depth=0)

        if not direct_call:
            current += 1
            current_task.update_state(state='PROGRESS',
                                      meta={'current': current, 'total': total})


@shared_task
def update_manualcase_error(case=None):
    """Check for errors in manual cases"""
    if not case:
        cases = WorkItem.objects.all()
    else:
        cases = [case]

    current = 0
    total = len(cases)
    direct_call = current_task.request.id is None

    for case in cases:
        case.error_check(depth=0)

        if not direct_call:
            current += 1
            current_task.update_state(state='PROGRESS',
                                      meta={'current': current, 'total': total})

@shared_task
def update_autocase_error(case=None):
    """Check for errors in auto cases"""
    if not case:
        cases = AutoCase.objects.all()
    else:
        cases = [case]

    current = 0
    total = len(cases)
    direct_call = current_task.request.id is None

    for case in cases:
        case.error_check(depth=0)

        if not direct_call:
            current += 1
            current_task.update_state(state='PROGRESS',
                                      meta={'current': current, 'total': total})


def _baseline_loader(baseline_file):
    with open('caselink/db_baseline/' + baseline_file) as base_fp:
        baseline = yaml.load(base_fp)
    return baseline


def _load_project_db(projects):
    for project_id, project_item in projects.items():
        Project.objects.create(
            id = project_id,
            name = project_item['name']
        )


def _load_error_db(errors):
    for error_id, error_item in errors.items():
        Error.objects.create(
            id = error_id,
            message = error_item['message']
        )


def _load_manualcase_db(polarion):
    for wi_id, case in polarion.items():

        # pylint: disable=no-member
        workitem, created = WorkItem.objects.get_or_create(id=wi_id)
        if not created:
            logging.error("Duplicated workitem '%s'" % wi_id)
            continue

        workitem.title = case['title']
        workitem.type = case['type']
        workitem.commit = case['commit']
        workitem.automation = 'automated' if case['automated'] else 'noautomated'

        workitem.project, created = Project.objects.get_or_create(name=case['project'])
        if created:
            logging.error("Created not included project '%s'" % case['project'])
            workitem.project.id = case['project']
            workitem.project.save()

        for arch_name in case['arch']:
            arch, _ = Arch.objects.get_or_create(name=arch_name)
            arch.workitems.add(workitem)
            arch.save()

        for doc_id in case['documents']:
            doc, created = Document.objects.get_or_create(id=doc_id)
            if created:
                doc.title = doc_id
                doc.component = Component.objects.get_or_create(name='libvirt')
            doc.workitems.add(workitem)
            doc.save()

        for error_message in case['errors']:
            error, created = Error.objects.get_or_create(message=error_message)
            if created:
                error.id = error_message
                logging.error("Created not included error '%s'" % error_message)
            error.workitems.add(workitem)
            error.save()

        workitem.save()


def _load_libvirt_ci_linkage_db(linkage):
    # pylint: disable=no-member
    for link in linkage:
        wi_ids = link.get('polarion', {}).keys()
        case_patterns = link.get('cases', [])
        automated = link.get('automated', True)
        framework = link.get('framework', 'libvirt-ci')
        comment = link.get('comment', '')
        feature = link.get('feature', '')
        title = link.get('title', '')

        framework, _ = Framework.objects.get_or_create(name=framework)

        #Legacy
        #tcms_ids = link.get('tcms', {}).keys()

        # Check for workitem deleted error
        # Create dummy workitem to track error
        for wi_id in wi_ids:
            wi, created = WorkItem.objects.get_or_create(id=wi_id)
            if created:
                wi.error = Error.objects.get(id="WORKITEM_DELETED")
                wi.save()

        # Create linkage
        for wi_id in wi_ids:
            workitem = WorkItem.objects.get(id=wi_id)
            for pattern in case_patterns:
                linkage, created = CaseLink.objects.get_or_create(
                    workitem=workitem,
                    autocase_pattern=pattern
                )
                if created:
                    linkage.framework = framework
                    linkage.title = title
                    linkage.save()
                else:
                    logging.error("Error in baseline db, duplicated linkage")
                    logging.error(str(workitem))
                    logging.error(str(pattern))


def _load_libvirt_ci_autocase_db(autocases):
    framework = "libvirt-ci"
    framework, _ = Framework.objects.get_or_create(name=framework)
    all_linkage = CaseLink.objects.all()

    for case_id in autocases:
        case = AutoCase.objects.create(
            id=case_id,
            framework=framework,
            #start_commit=commit
            #end_commit=commit
        )

        arch, _ = Arch.objects.get_or_create(name='')
        case.archs.add(arch)
        case.save()

        for caselink in all_linkage:
            if caselink.test_match(case):
                caselink.autocases.add(case)
                caselink.save()


def _load_failure_and_bug(failures):
    for failure in failures:
        fail_regex = failure.get('fail-regex', None)
        bug_id = failure.get('bug', None)
        auto_patterns = failure.get('autocases', [])
        skip = failure.get('skip', None)
        if (bug_id and skip) or (not bug_id and not skip):
            print "Bad entry: " + str(failure)
            continue

        bug = None
        if bug_id:
            bug = Bug.objects.create(id=bug_id)
            for manualcase in failure['workitems']:
                manualcase = WorkItem.objects.get(id=manualcase)
                bug.manualcases.add(manualcase)
            bug.save()

        for pattern in auto_patterns:
            case_failure = AutoCaseFailure.objects.create(
                autocase_pattern=pattern,
                type="CASE-UPDATE" if skip else "BUG",
                failure_regex=fail_regex,
                bug=bug
            )
            case_failure.autolink()
