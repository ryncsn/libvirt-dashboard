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


def _baseline_loader(baseline_file):
    with open('caselink/db_baseline/' + baseline_file) as base_fp:
        baseline = yaml.load(base_fp)
    return baseline


def load_error():
    """Load baseline Error"""
    _load_error_db(_baseline_loader('base_error.yaml'))


def load_project():
    """Load baseline Project"""
    _load_project_db(_baseline_loader('base_project.yaml'))


def load_manualcase():
    """Load baseline Manual cases"""
    _load_manualcase_db(_baseline_loader('base_workitem.yaml'))
    updata_manualcase_error()


def load_autocase_linkage():
    """Load baseline Auto cases and linkage"""
    _load_autocase_linkage_db(_baseline_loader('base_autocase_linkage.yaml'))
    updata_linkage_error()
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


@transaction.atomic
def _load_project_db(projects):
    for project_id, project_item in projects.items():
        project, _ = Project.objects.get_or_create(id=project_id)
        project.name = project_item['name']
        project.save()


@transaction.atomic
def _load_error_db(errors):
    for error_id, error_item in errors.items():
        error, _ = Error.objects.get_or_create(id=error_id)
        error.message = error_item['message']
        error.save()


@transaction.atomic
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


@transaction.atomic
def _load_autocase_linkage_db(linkage):
    # pylint: disable=no-member
    for link in linkage:
        wi_ids = link.get('polarion', {}).keys()
        case_names = link.get('cases', [])
        automated = link.get('automated', True)
        framework = link.get('framework', '')
        tcms_ids = link.get('tcms', {}).keys()
        comment = link.get('comment', '')
        feature = link.get('feature', '')
        title = link.get('title', '')
        autocase_errors = set()
        workitem_errors = set()
        linkage_errors = set()

        # Check for workitem number error
        if not wi_ids:
            logging.error("No Polarion specified in linkage for %s",
                          link.get('title', ''))
            autocase_errors.add("NO_WORKITEM")
        elif len(wi_ids) > 1:
            logging.error("More than one polarion for one linkage for %s: %s",
                          link.get('title', ''), wi_ids)
            autocase_errors.add("MULTIPLE_WORKITEM")

        # Check for workitem deleted error
        # Create dummy workitem to track error
        for wi_id in wi_ids:
            wi, created = WorkItem.objects.get_or_create(id=wi_id)
            if created:
                logging.error("Work Item %s in linkage not found on Polarion",
                              wi_id)
                linkage_errors.add("WORKITEM_DELETED")
                workitem_errors.add("WORKITEM_DELETED")
                try:
                    wi.error = Error.objects.get(id="WORKITEM_DELETED")
                except ObjectDoesNotExist:
                    logging.error("Error WORKITEM_DELETED not found")
                wi.save()
                continue
            elif len(wi_ids) == 1 and wi.title != title:
                logging.error("Work Item %s in linkage have diffrent title on Polarion",
                              wi_id)
                linkage_errors.add("WORKITEM_TITLE_INCONSISTENCY")
                workitem_errors.add("WORKITEM_TITLE_INCONSISTENCY")

        # Create autocase
        for name in case_names:
            case, created = AutoCase.objects.get_or_create(id=name)
            for err in autocase_errors:
                case.errors.add(Error.objects.get(id=err))
            # Fill new created autocase entry
            if created:
                framework, _ = Framework.objects.get_or_create(name=framework)
                case.framework = framework
                #case.archs=Framework.objects.get_or_create(name=framework)
                #case.start_commit=Framework.objects.get_or_create(name=framework)
                #case.end_commit=Framework.objects.get_or_create(name=framework)
            case.save()

        # Create linkage
        for wi_id in wi_ids:
            workitem = WorkItem.objects.get(id=wi_id)
            linkage, created = CaseLink.objects.get_or_create(workitem=workitem)
            #if created:
                #linkage.framework=Framework.objects.get_or_create(name=framework)
            for name in case_names:
                linkage.autocases.add(AutoCase.objects.get(id=name))

            if workitem.automation != automated and len(case_names) > 0:
                workitem.automation = 'automated'
                workitem.errors.add("WORKITEM_AUTOMATION_INCONSISTENCY")
            workitem.feature = feature
            for err in workitem_errors:
                workitem.errors.add(Error.objects.get(id=err))
            workitem.save()

            for err in linkage_errors:
                linkage.errors.add(Error.objects.get(id=err))
            linkage.save()
