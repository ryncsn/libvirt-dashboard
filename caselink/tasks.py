"""
Celery asynchronous tasks
"""
import yaml
import re
import logging
import difflib

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from celery import shared_task

# pylint: disable=redefined-builtin
from builtins import str
from pylarion.document import Document as PylarionDocument
from html.parser import HTMLParser
from jira import JIRA

from caselink.models import WorkItem, Document, Change
from caselink.models import AvocadoCase, TCMSCase, Error


@shared_task
def update_polarion():
    _update_polarion_db(_load_polarion())
    update_changes()


@shared_task
def update_linkage():
    _update_linkage_db(_load_linkage())


@shared_task
def update_changes():
    updates = _load_updates()
    _update_changes_db(updates)


@shared_task
def create_jira_issue(wi_id):
    options = {
        'server': 'https://projects.engineering.redhat.com',
        'verify': False,
    }

    basic_auth = ('username', 'password')
    jira = JIRA(options, basic_auth=basic_auth)

    # Change contnent of this.
    issue_dict = {
        'project': {
            'key': 'LIBVIRTAT',
        },
        'summary': 'Update autocase for %s' % wi_id,
        'description': '',
        'parent': {
            'id': 'LIBVIRTAT-19',
        },
        'issuetype': {
            'name': 'Sub-task',
        },
    }
    jira.create_issue(fields=issue_dict)


def _load_polarion():
    # TODO: remove the function
    def _flatten_cases(cases):
        all_cases = {}
        for doc_id, doc in cases['documents'].items():
            wis = doc['work_items']
            for wi_id, wi in wis.items():
                if 'documents' in wi:
                    wi['documents'].append(doc_id)
                else:
                    wi['documents'] = [doc_id]
                all_cases[wi_id] = wi
        return all_cases
    project = 'RedHatEnterpriseLinux7'
    space = 'Virt-LibvirtQE'
    obj = {
        'project': unicode(project),
        'space': unicode(space),
        'documents': {},
    }

    docs = PylarionDocument.get_documents(
        project, space, fields=['document_id', 'title', 'type', 'updated'])
    print(u'Found %d documents project:%s space:%s' %
          (len(docs), project, space))
    for doc in docs:
        print('  - ', doc.title)

    for doc_idx, doc in enumerate(docs):
        obj_doc = {
            'title': unicode(doc.title),
            'type': unicode(doc.type),
            'updated': doc.updated,
            'work_items': {},
        }

        print(u'Reading (%2d/%2d) %-20s %-60s' %
              (doc_idx + 1, len(docs), doc.type, doc.title))
        fields = ['work_item_id', 'type', 'title', 'updated']
        wis = doc.get_work_items(None, True, fields=fields)
        for wi_idx, wi in enumerate(wis):
            obj_wi = {
                'title': str(wi.title),
                'type': str(wi.type),
                'updated': wi.updated,
            }
            obj_doc['work_items'][str(wi.work_item_id)] = obj_wi
        obj['documents'][str(doc.document_id)] = obj_doc
    return _flatten_cases(obj)


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
def _update_polarion_db(cases):
    # pylint: disable=no-member
    early_error, _ = Error.objects.get_or_create(
        name='Current date earlier than confirmation')

    for wi_id, case in cases.items():
        wi, created = WorkItem.objects.get_or_create(wi_id=wi_id)
        wi.title = case['title']
        wi.type = case['type']
        updated = timezone.make_aware(case['updated'])
        if created:
            wi.updated = wi.confirmed = updated
        else:
            if wi.confirmed < updated:
                print("Current date late than confirmation for %s (%s:%s)" %
                      (updated - wi.confirmed, wi.confirmed, updated))
                wi.updated = updated
            elif wi.confirmed > updated:
                print("Current date earlier than confirmation for %s (%s:%s)" %
                      (wi.confirmed - updated, wi.confirmed, updated))
                wi.errors.add(early_error)
        wi.save()

        for doc_id in case['documents']:
            doc, _ = Document.objects.get_or_create(doc_id=doc_id)
            doc.workitems.add(wi)
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


def _convert_text(text):
    lines = re.split(r'\<[bB][rR]/\>', text)
    new_lines = []
    for line in lines:
        line = " ".join(line.split())
        line = HTMLParser().unescape(line)
        new_lines.append(line)
    return '\n'.join(new_lines)


def _diff_test_steps(before, after):
    steps_before = before['steps']['TestStep']
    steps_after = after['steps']['TestStep']

    if not isinstance(steps_before, list):
        steps_before = [steps_before]
    if not isinstance(steps_after, list):
        steps_after = [steps_after]

    diff_txt = ''
    if len(steps_before) == len(steps_after):
        for idx in range(len(steps_before)):
            step_before, result_before = [
                _convert_text(text['content'])
                for text in steps_before[idx]['values']['Text']]
            step_after, result_after = [
                _convert_text(text['content'])
                for text in steps_after[idx]['values']['Text']]
            if step_before != step_after:
                diff_txt += 'Step %s changed:\n' % (idx + 1)
                for line in difflib.unified_diff(step_before.splitlines(1),
                                                 step_after.splitlines(1)):
                    diff_txt += line
                diff_txt += '\n'
            if result_before != result_after:
                diff_txt += 'Result %s changed:\n' % (idx + 1)
                for line in difflib.unified_diff(result_before.splitlines(1),
                                                 result_after.splitlines(1)):
                    diff_txt += line
                diff_txt += '\n'
    else:
        diff_txt = ('Steps count changed %s --> %s' %
                    (len(steps_before), len(steps_after)))
    return diff_txt


def _check_diff(diff, wi_id=None):
    field = diff['fieldName']
    # Ignore irrelevant properties changing
    if field in [
            'updated', 'outlineNumber', 'caseautomation', 'status',
            'previousStatus', 'approvals', 'tcmscaseid']:
        return (field, None)

    # Ignore parent item changing
    if (field == 'linkedWorkItems' and
            diff['added'] and diff['removed'] and
            len(diff['added']['item']) == 1 and
            len(diff['removed']['item']) == 1 and
            diff['added']['item'][0]['role']['id'] == 'parent' and
            diff['removed']['item'][0]['role']['id'] == 'parent'):
        return (field, None)

    after_txt = ''
    before_txt = ''

    if diff['added']:
        adds = diff['added']['item']
        for add in adds:
            after_txt += str(add) + '\n'
    if diff['removed']:
        removes = diff['removed']['item']
        for remove in removes:
            before_txt += str(remove) + '\n'

    if 'before' in diff or 'after' in diff:
        before = diff.get('before', '')
        after = diff.get('after', '')

        if 'id' in before:
            before = before['id']
        if 'id' in after:
            after = after['id']
        if 'content' in before:
            before = _convert_text(before['content'])
        if 'content' in after:
            after = _convert_text(after['content'])

        before_txt += str(before) + '\n'
        after_txt += str(after) + '\n'

    if field == 'testSteps':
        diff_txt = _diff_test_steps(before, after)
    else:
        diff_txt = ''
        for line in difflib.unified_diff(
                before_txt.splitlines(1),
                after_txt.splitlines(1)):
            diff_txt += line

    return (field, diff_txt)


@transaction.atomic
def _update_changes_db(updates):
    # pylint: disable=no-member
    changed_error, _ = Error.objects.get_or_create(
        name='Updates not confirmed')

    for wi_id, changes in updates.items():
        wi = WorkItem.objects.get(wi_id=wi_id)
        if wi.automation != 'automated':
            continue

        # Sort changes according to revision numbers
        changes = sorted(changes, key=lambda change: int(change['revision']))

        changed = False
        for change_obj in changes:
            diffs = {}
            for diff in change_obj['diffs']['item']:
                field, diff_txt = _check_diff(diff)
                if diff_txt:
                    diffs[field] = diff_txt

            if diffs:
                revision = change_obj['revision']
                change, _ = Change.objects.get_or_create(
                    workitem=wi,
                    revision=revision,
                )
                change.obj = yaml.dump(change_obj)
                txt = ''
                for field, diff_txt in diffs.items():
                    txt += field + '\n'
                    txt += diff_txt + '\n'
                change.diff = txt
                change.save()
                changed = True
                wi.errors.add(changed_error)
            else:
                # Update confirmed timestamps until major change found
                if not changed:
                    wi.confirmed = timezone.make_aware(change_obj['date'])
        wi.save()
