#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from collections import OrderedDict

import re
import datetime
import HTMLParser
import difflib
import json
import yaml
import copy
import sys
import suds

from pylarion.document import Document
from pylarion.enum_option_id import EnumOptionId
from pylarion.work_item import _WorkItem
from pylarion.wiki_page import WikiPage


def exc_hook(exctype, value, trace):
    """
    Customized exception hook function to enable pdb when unhandled
    exception raised.
    """
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
        # We are in interactive mode or we don't have a tty-like
        # device, so we call the default hook
        sys.__excepthook__(exctype, value, trace)
    else:
        import pdb
        import traceback
        # We are NOT in interactive mode, print the exception...
        traceback.print_exception(exctype, value, trace)
        print()
        # ...then start the debugger in post-mortem mode.
        pdb.pm()

# Override exception hook to jump into pdb when exception
sys.excepthook = exc_hook

PROJECT = 'RedHatEnterpriseLinux7'

AUTO_SPACE = 'Virt-LibvirtAuto'
MANUAL_SPACE = 'Virt-LibvirtQE'
service = _WorkItem.session.tracker_client.service


def info(text, *args):
    print(text % args)


def wiki_escape(text):
    text = text.replace('[', '\\[')
    text = text.replace(']', '\\]')
    text = text.replace('-', '\\-')
    return text


class literal(unicode):
    pass


def literal_presenter(dumper, data):
    style = '"'
    if '\n' in data:
        style = '|'
    elif len(data) > 70:
        style = '>'
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)


def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())


def suds_2_object(suds_obj):
    obj = OrderedDict()
    for key, value in suds_obj.__dict__.items():
        if key.startswith('_'):
            continue

        if isinstance(value, suds.sax.text.Text):
            value = literal(value.strip())
        elif isinstance(value, (bool, int, datetime.date, datetime.datetime)):
            pass
        elif value is None:
            pass
        elif isinstance(value, list):
            value_list = []
            for elem in value:
                value_list.append(suds_2_object(elem))
            value = value_list
        elif hasattr(value, '__dict__'):
            value = suds_2_object(value)
        else:
            print('Unhandled value type: %s' % type(value))

        obj[key] = value
    return obj


def load_polarion(project, space):
    obj = OrderedDict([
        ('project', literal(project)),
        ('space', literal(space)),
        ('documents', OrderedDict()),
    ])

    docs = Document.get_documents(
        project, space, fields=['document_id', 'title', 'type', 'updated', 'project_id'])
    info(u'Found %d documents project:%s space:%s', len(docs), project, space)
    for doc in docs:
        print('  - ', doc.title)

    for doc_idx, doc in enumerate(docs):
        obj_doc = OrderedDict([
            ('title', literal(doc.title)),
            ('type', literal(doc.type)),
            ('project', project),
            ('work_items', OrderedDict()),
            ('updated', doc.updated),
        ])

        info(u'Reading (%2d/%2d) %-20s %-60s',
             doc_idx + 1, len(docs), doc.type, doc.title)
        fields = ['work_item_id', 'type', 'title', 'updated']
        wis = doc.get_work_items(None, True, fields=fields)
        for wi_idx, wi in enumerate(wis):
            obj_wi = OrderedDict([
                ('title', literal(wi.title)),
                ('type', literal(wi.type)),
                ('project', project),
                ('updated', wi.updated),
            ])
            obj_doc['work_items'][literal(wi.work_item_id)] = obj_wi
        obj['documents'][literal(doc.document_id)] = obj_doc
    return flatten_cases(obj)


def check_updates(param):
    new_cases = param['current']
    old_cases = param['base']

    assert new_cases['project'] == old_cases['project']
    assert new_cases['space'] == old_cases['space']
    project = new_cases['project']
    space = new_cases['space']

    new_doc_ids = set(new_cases['documents'].keys())
    old_doc_ids = set(old_cases['documents'].keys())
    created_docs = new_doc_ids - old_doc_ids
    removed_docs = new_doc_ids - old_doc_ids

    if created_docs:
        info('Created documents in %s %s:', project, space)
        for doc_id in created_docs:
            info('   %s' % doc_id)
    if removed_docs:
        info('Removed documents in %s %s:', project, space)
        for doc_id in created_docs:
            info('   %s', doc_id)

    for doc_id in (new_doc_ids & old_doc_ids):
        old_wis = old_cases['documents'][doc_id]['work_items']
        new_wis = new_cases['documents'][doc_id]['work_items']

        old_wi_ids = set(old_wis.keys())
        new_wi_ids = set(new_wis.keys())
        created_wis = new_wi_ids - old_wi_ids
        removed_wis = old_wi_ids - new_wi_ids

        if created_wis:
            info("Created work items in %s:", doc_id)
            for wi_id in created_wis:
                info('   %s' % wi_id)
        if removed_wis:
            info("Removed work items in %s:", doc_id)
            for wi_id in removed_wis:
                info('   %s', wi_id)

        for wi_id in (new_wi_ids & old_wi_ids):
            old_wi = new_wis[wi_id]
            new_wi = new_wis[wi_id]

            if new_wi['updated'] != old_wi['updated']:
                info('Work item %s: %s has been updated at %s',
                     (wi_id, new_wi['title'], new_wi['updated']))


def flatten_cases(cases):
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


def check_linkage(cases, linkage):
    no_polarion = []
    multiple_polarion = []
    polarion_not_found = []
    no_existing_polarion = []
    unmarked_polarion = []
    for case in linkage:
        if 'polarion' in case and case['polarion']:
            existing_polarions = []
            for wi_id in case['polarion']:
                if wi_id in cases:
                    existing_polarions.append(wi_id)
                else:
                    unmarked_polarion.append(wi_id)

            if len(existing_polarions) > 1:
                multiple_polarion.append(case)
            elif len(existing_polarions) == 0:
                no_existing_polarion.append(case)
        else:
            no_polarion.append(case)
    print('Found %3d linkages without polarion work item' % len(no_polarion))
    print('=' * 80)
    for case in no_polarion:
        print('%20sTCMS:%7s' % (case['feature'], max(case['tcms'].keys())),
              case['title'])
    same_title = []
    different_title = []
    for case in multiple_polarion:
        titles = [cases[wi_id]['title'] for wi_id in case['polarion'].keys()]
        if titles.count(titles[0]) == len(titles):
            same_title.append(case)
        else:
            different_title.append(case)

    print('Found %3d linkages polarion work item unmarked' %
          len(unmarked_polarion))
    print('=' * 80)
    for wi_id in unmarked_polarion:
        print(wi_id)

    print('Found %3d linkages with many polarion work items with same title'
          % len(same_title))
    print('=' * 80)
    for case in same_title:
        for wi_id in case['polarion'].keys():
            print('  ', wi_id)
            print('    ', cases[wi_id]['title'], cases[wi_id]['documents'])
        print('~' * 80)
    print('Found %3d linkages with many polarion work items with '
          'different titles' % len(different_title))
    print('=' * 80)
    for case in different_title:
        for wi_id in case['polarion'].keys():
            print('  ', wi_id)
            print('    ', cases[wi_id]['title'], cases[wi_id]['documents'])
        print('~' * 80)
    print('Found %3d linkages with zero polarion work item' %
          len(no_existing_polarion))
    print('=' * 80)
    for case in no_existing_polarion:
        print(case['title'])
        print('  %s' % case['polarion'].keys())
        print('~' * 80)
    print('Found %3d linkages with polarion work item not found' %
          len(polarion_not_found))
    print('=' * 80)


def update_automation(linkage):
    for case in linkage:
        if 'automated' not in case:
            case['automated'] = True
        if 'polarion' not in case:
            case['polarion'] = {}

    # TODO: Check all manual cases. Not only automated cases.
    session = _WorkItem.session
    session.tx_begin()
    for case in linkage:
        if case['automated']:
            wi_ids = case['polarion'].keys()
            for wi_id in wi_ids:
                automation = None
                wi = _WorkItem(project_id=PROJECT, work_item_id=wi_id)
                for custom in wi._suds_object.customFields.Custom:
                    if custom.key == 'caseautomation':
                        automation = custom.value.id

                if automation in ['notautomated', None]:
                    print("Setting %s" % wi_id)
                    value = EnumOptionId(enum_id='automated')
                    wi._set_custom_field('caseautomation', value._suds_object)
                else:
                    print("%s have automation state: %s" % (wi_id, automation))
    session.tx_commit()


def update_json(all_cases):
    json_obj = []
    for case in all_cases:
        if case['type'] == 'heading':
            continue
        if case['updated']:
            case['updated'] = case['updated'].isoformat()
        case['documents'] = '<br/>'.join(case['documents'])
        case['errors'] = '<br/>'.join(case['errors'])
        case['changes'] = ''
        json_obj.append(case)

    with open('data.json', 'w') as json_fp:
        json.dump({'data': json_obj}, json_fp, indent=4)


def merge_cases(base, current, updates, linkage):
    polarion_dict = current

    linkage_dict = {}
    for case in linkage:
        if 'polarion' in case and case['polarion']:
            if len(case['polarion']) > 1:
                print('Multiple polarion for %s %s' %
                      (case['title'], case['polarion'].keys()))
            for wi_id in case['polarion']:
                result_case = copy.deepcopy(case)
                result_case['tcms'] = case.get('tcms', {}).keys()
                result_case['automated'] = case.get('automated', True)
                linkage_dict[wi_id] = result_case
        else:
            print('%s do not have polarion' % case['title'])

    defaults = {
        'title': '',
        'polarion': '',
        'tcms': '',
        'feature': '',
        'comment': '',
        'automated': False,
        'el6': True,
        'el7': True,
        'type': '',
        'updated': None,
        'created': False,
        'removed': False,
    }

    all_cases = []
    polarion_ids = set(linkage_dict) | set(base) | set(current)
    for wi_id in polarion_ids:
        polarion_case = polarion_dict.get(wi_id, {})
        linkage_case = linkage_dict.get(wi_id, {})
        updates_case = updates.get(wi_id, {})

        case = {}
        for key in defaults:
            if key in polarion_case:
                case[key] = polarion_case.get(key)
            elif key in linkage_case:
                case[key] = linkage_case.get(key)
            elif key in updates_case:
                case[key] = updates_case.get(key)
            else:
                case[key] = defaults[key]
        for key in ['cases', 'documents', 'errors', 'changes', 'diffs']:
            if key in polarion_case:
                case[key] = polarion_case.get(key)
            elif key in linkage_case:
                case[key] = linkage_case.get(key)
            elif key in updates_case:
                case[key] = updates_case.get(key)
            else:
                case[key] = []
        case['polarion'] = wi_id
        all_cases.append(case)
    return all_cases


def recent_changes(wi_id, start):
    uri = 'subterra:data-service:objects:/default/%s${WorkItem}%s' % (
        PROJECT, wi_id)
    changes = service.generateHistory(uri)
    latest_changes = []
    for change in changes:
        if change.date > start:
            latest_changes.append(suds_2_object(change))
    return latest_changes


def convert_text(text):
    lines = re.split(r'\<[bB][rR]/\>', text)
    new_lines = []
    for line in lines:
        line = " ".join(line.split())
        line = HTMLParser.HTMLParser().unescape(line)
        new_lines.append(line)
    return '\n'.join(new_lines)


def diff_test_steps(before, after):
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
                convert_text(text['content'])
                for text in steps_before[idx]['values']['Text']]
            step_after, result_after = [
                convert_text(text['content'])
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


def check_changes(changes, wi_id=None):
    diffs = []
    for change in changes:
        for diff in change['diffs']['item']:
            field = diff['fieldName']
            # Ignore irrelevant properties changing
            if field in [
                    'updated', 'outlineNumber', 'caseautomation', 'status',
                    'previousStatus', 'approvals', 'tcmscaseid']:
                continue

            # Ignore parent item changing
            if (field == 'linkedWorkItems' and
                    diff['added'] and diff['removed'] and
                    len(diff['added']['item']) == 1 and
                    len(diff['removed']['item']) == 1 and
                    diff['added']['item'][0]['role']['id'] == 'parent' and
                    diff['removed']['item'][0]['role']['id'] == 'parent'):
                continue

            result_diff = {'field': field, 'added': [], 'removed': [],
                           'changed': ''}

            if diff['added']:
                adds = diff['added']['item']
                for add in adds:
                    result_diff['added'].append(add)

            if diff['removed']:
                removes = diff['removed']['item']
                for remove in removes:
                    result_diff['removed'].append(remove)

            if 'before' in diff or 'after' in diff:
                before = diff.get('before', '')
                after = diff.get('after', '')

                if field == 'testSteps':
                    result_diff['changed'] = diff_test_steps(before, after)
                    diffs.append(result_diff)
                    continue

                if 'id' in before:
                    before = before['id']
                if 'id' in after:
                    after = after['id']
                if 'content' in before:
                    before = convert_text(before['content'])
                if 'content' in after:
                    after = convert_text(after['content'])
                before += '\n'
                after += '\n'

                diff_txt = ''
                for line in difflib.unified_diff(
                        before.splitlines(1),
                        after.splitlines(1)):
                    diff_txt += line
                result_diff['changed'] = diff_txt
                diffs.append(result_diff)
    return diffs


def load_updates(base, current):
    created = set(current) - set(base)
    removed = set(base) - set(current)
    all_cases = set(base) | set(current)

    print('Created %s work items:' % len(created))
    print('Removed %s work items:' % len(removed))

    with open('updates.yaml') as updates_fp:
        old_updates = yaml.load(updates_fp)

    updates = {}
    for wi_id in all_cases:
        if wi_id in created:
            updates[wi_id] = {'created': True}
        elif wi_id in removed:
            updates[wi_id] = {'removed': True}
        else:
            if wi_id in old_updates:
                updates[wi_id] = {'changes': old_updates[wi_id]}
                continue

            base_wi = base[wi_id]
            current_wi = current[wi_id]
            if base_wi['updated'] != current_wi['updated']:
                print('%s changed on %s' % (wi_id, current_wi['updated']))
                changes = recent_changes(wi_id, base_wi['updated'])
                updates[wi_id] = {'changes': changes}

    # updates = {}
    # for wi_id in unchanged:
    #     base_wi = base[wi_id]
    #     current_wi = current[wi_id]
    #     if base_wi['updated'] != current_wi['updated']:
    #         print('%s changed on %s' % (wi_id, current_wi['updated']))
    #         changes = recent_changes(wi_id, base_wi['updated'])
    #         updates[wi_id] = changes

    with open('updates.yaml', 'w') as updates_fp:
        yaml.dump(updates, updates_fp)

    with open('updates.yaml') as updates_fp:
        updates = yaml.load(updates_fp)
    return updates


def load():
    # Load base status recorded
    with open('base_polarion.yaml') as base_fp:
        base = yaml.load(base_fp)

    # Load current polarion status
    # current = load_polarion(project, MANUAL_SPACE)
    with open('current_polarion.yaml') as current_fp:
        current = yaml.load(current_fp)

    # Load linkage configured
    with open('autotest_cases.yaml') as linkage_fp:
        linkage = yaml.load(linkage_fp)

    # Load updates
    # updates = load_updates(base, current)
    with open('updates.yaml') as updates_fp:
        updates = yaml.load(updates_fp)

    return merge_cases(base, current, updates, linkage)


def check(cases):
    """
    Check all the data collected and mark corresponding error message if
    error exists.
    """
    def _find_duplicates(cases):
        observed_titles = {}
        for case in cases:
            title = case['title']
            wi_id = case['polarion']

            # Collect occurrences of same titles.
            if title in observed_titles:
                if wi_id not in observed_titles[title]:
                    observed_titles[title].append(wi_id)
            else:
                observed_titles[title] = [wi_id]

        return {title: wis for title, wis in observed_titles.items()
                if len(wis) > 1}

    # Filter away heading cases and removed, not-automated cases.
    cases = [case for case in cases if case['type'] != 'heading' and
             not (case['removed'] and not case['automated'])]

    duplicates = _find_duplicates(cases)

    for case in cases:
        wi_id = case['polarion']

        if wi_id and not case['documents']:
            case['errors'].append('Polarion work item unmarked')

        if case['title'] in duplicates:
            case['errors'].append('Duplicate name found')

        if case['changes']:
            case['diffs'] = check_changes(case['changes'], wi_id)
            if case['diffs'] and case['automated']:
                case['errors'].append('Updates not confirmed')
            else:
                case['accept_updates'] = True


def update_base(cases):
    new_base = {}
    for case in cases:
        new_case = {}
        wi_id = case['polarion']
        new_case['documents']

        new_base[wi_id] = new_case
    with open('base_polarion_new.yaml', 'w') as base_fp:
        yaml.dump(new_base, base_fp)


def run():
    # Load stage
    all_cases = load()

    # Check stage
    check(all_cases)
#    linkage_result = check_linkage(current, linkage)

    # Update stage
    # update_automation(linkage)
    update_base(all_cases)
    update_json(all_cases)

    # Report stage
    # report(polarion_result)


if __name__ == '__main__':
    yaml.add_representer(literal, literal_presenter)
    yaml.add_representer(OrderedDict, ordered_dict_presenter)
    run()
