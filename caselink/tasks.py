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

from caselink.models \
        import Error, Arch, Component, Framework, Project, Document, WorkItem, AutoCase, CaseLink


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
    updata_manualcase_error()


@transaction.atomic
def load_linkage():
    """Load baseline linkage"""
    _load_libvirt_ci_linkage_db(_baseline_loader('base_libvirt_ci_linkage.yaml'))
    updata_autocase_error()


@transaction.atomic
def load_autocase():
    """Load baseline Auto cases"""
    _load_libvirt_ci_autocase_db(_baseline_loader('base_libvirt_ci_autocase.yaml'))
    updata_autocase_error()


def updata_linkage_error():
    """Check for errors in linkage"""
    pass


def updata_manualcase_error():
    """Check for errors in manual cases"""
    pass


def updata_autocase_error():
    """Check for errors in auto cases"""
    pass


def _baseline_loader(baseline_file):
    with open('caselink/db_baseline/' + baseline_file) as base_fp:
        baseline = yaml.load(base_fp)
    return baseline


def _load_project_db(projects):
    for project_id, project_item in projects.items():
        project, _ = Project.objects.get_or_create(id=project_id)
        project.name = project_item['name']
        project.save()


def _load_error_db(errors):
    for error_id, error_item in errors.items():
        error, _ = Error.objects.get_or_create(id=error_id)
        error.message = error_item['message']
        error.save()


def _load_manualcase_db(polarion):
    for wi_id, case in polarion.items():

        # pylint: disable=no-member
        workitem, _ = WorkItem.objects.get_or_create(id=wi_id)
        workitem.title = case['title']
        workitem.type = case['type']
        workitem.automation = case['automated']
        workitem.commit = case['commit']
        workitem.arch, _ = Arch.objects.get_or_create(name=case['arch'])
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
        workitem_errors = set()
        linkage_errors = set()

        framework, _ = Framework.objects.get_or_create(name=framework)

        #Legacy
        #tcms_ids = link.get('tcms', {}).keys()

        # Check for workitem number error
        if len(wi_ids) > 1:
            logging.error("More than one polarion for one linkage for %s: %s",
                          link.get('title', ''), wi_ids)
            linkage_errors.add("PATTERN_DUPLICATE")
            workitem_errors.add("PATTERN_DUPLICATE")

        # Check for workitem deleted error
        # Create dummy workitem to track error
        for wi_id in wi_ids:
            wi, created = WorkItem.objects.get_or_create(id=wi_id)
            if created:
                logging.error("Work Item %s in linkage deleted on Polarion", wi_id)
                linkage_errors.add("WORKITEM_DELETED")
                workitem_errors.add("WORKITEM_DELETED")
                wi.error = Error.objects.get(id="WORKITEM_DELETED")
                wi.save()
            elif wi.title != title:
                logging.error("Work Item %s in linkage have diffrent title on Polarion", wi_id)
                linkage_errors.add("WORKITEM_TITLE_INCONSISTENCY")
                workitem_errors.add("WORKITEM_TITLE_INCONSISTENCY")

        # Create linkage
        for wi_id in wi_ids:
            workitem = WorkItem.objects.get(id=wi_id)
            for pattern in case_patterns:
                linkage, created = CaseLink.objects.get_or_create(
                    workitem=workitem, autocase_pattern=pattern)
                if created:
                    linkage.framework = framework
                    linkage.title = title

                for err in linkage_errors:
                    linkage.errors.add(Error.objects.get(id=err))
                linkage.save()

            # Check for error
            if workitem.automation != automated and len(case_patterns) > 0:
                workitem.automation = 'automated'
                workitem.errors.add("WORKITEM_AUTOMATION_INCONSISTENCY")

            for err in workitem_errors:
                workitem.errors.add(Error.objects.get(id=err))
            workitem.save()


def _load_libvirt_ci_autocase_db(autocases):
    framework = "libvirt-ci"
    framework, _ = Framework.objects.get_or_create(name=framework)
    all_linkage = CaseLink.objects.all()
    count = 0

    def test_match(patt_str, test_str):
        """
        Test if a test name match with the name pattern.
        """
        segments = patt_str.split('..')
        items = test_str.split('.')
        idx = 0
        for segment in segments:
            seg_items = segment.split('.')
            try:
                while True:
                    idx = items.index(seg_items[0])
                    if items[idx:len(seg_items)] == seg_items:
                        items = items[len(seg_items):]
                        break
                    else:
                        del items[0]
            except ValueError:
                return False
        return True

    for case_id in autocases:
        case, created = AutoCase.objects.get_or_create(
            id=case_id,
            framework=framework
            #archs=Arch.objects.get_or_create(name=arch)
            #start_commit=commit
            #end_commit=commit
        )

        for caselink in all_linkage:
            if test_match(caselink.autocase_pattern, case_id):
                caselink.autocases.add(case)

        if len(case.caselinks.all()) < 1:
            case.errors.add(Error.objects.get(id="NO_WORKITEM"))
            case.save()

    for caselink in all_linkage:
        caselink.save()
