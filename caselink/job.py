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


PROJECT = 'RedHatEnterpriseLinux7'
AUTO_SPACE = 'Virt-LibvirtAuto'
MANUAL_SPACE = 'Virt-LibvirtQE'


ALL_CASE_DEFAULT_ATTR = {
    'polarion': '',
    'title': '',
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
    'project': PROJECT,
    'component': 'libvirt',
    'cases': [],
    'documents': [],
    'errors': [],
    'changes': [],
    'diffs': [],
}


BASELINE_WORKITEM_ATTR = {
    'title': '',
    'type': '',
    'automated': '',
    'commit': '',
    'arch': '',
    'documents': '',
    'component': 'libvirt',
    'project': PROJECT,
    'updated': '',
    'errors': ['Empty error'],
}


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
service = _WorkItem.session.tracker_client.service


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


def load_polarion(project, space):
    obj = OrderedDict([
        ('project', literal(project)),
        ('space', literal(space)),
        ('documents', OrderedDict()),
    ])

    docs = Document.get_documents(
        project, space, fields=['document_id', 'title', 'type', 'updated', 'project_id'])
    print(u'Found %d documents project:%s space:%s' % (len(docs), project, space))
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

        print(u'Reading (%2d/%2d) %-20s %-60s' %
             (doc_idx + 1, len(docs), doc.type, doc.title))
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


def check_and_load_automated(cases, linkage):
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


def check_and_merge_cases(cases, linkage):
    """
    Merge workitem dict and linkage array into a list
    Print all errors founded
    """
    polarion_dict = cases

    linkage_dict = {}
    for case in linkage:
        if 'polarion' in case and case['polarion']:
            if len(case['polarion']) > 1:
                print('Multiple polarion for %s %s' %
                      (case['title'], case['polarion'].keys()))
            for wi_id in case['polarion']:
                if wi_id not in polarion_dict:
                    print('Polarion workitem deleted' + str(wi_id))
                    continue
                if wi_id in linkage_dict:
                    print('Merge cases list for' + str(wi_id))
                    result_case = linkage_dict[wi_id]
                    if case['feature'] != result_case['feature']:
                        print('Merge failed' + str(wi_id))
                    print(result_case.keys())
                    print(case.keys())
                    result_case['cases'] += case['cases']
                    result_case['tcms'] += case.get('tcms', {}).keys()
                else:
                    result_case = copy.deepcopy(case)
                    result_case['tcms'] = case.get('tcms', {}).keys()
                    result_case['automated'] = case.get('automated', True)
                    linkage_dict[wi_id] = result_case
        else:
            print('%s do not have polarion' % case['title'])

    defaults = ALL_CASE_DEFAULT_ATTR
    all_cases = []
    all_cases_ids = set(linkage_dict) | set(polarion_dict)
    for wi_id in all_cases_ids:
        polarion_case = polarion_dict.get(wi_id, {})
        linkage_case = linkage_dict.get(wi_id, {})

        case = {}
        for key in defaults:
            if key in polarion_case:
                case[key] = polarion_case.get(key)
            elif key in linkage_case:
                case[key] = linkage_case.get(key)
            else:
                case[key] = defaults[key][:] if isinstance(defaults[key], list) else defaults[key]
        case['polarion'] = wi_id
        all_cases.append(case)
    return all_cases


def check_cases_list(cases):
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


def update_base(cases):
    new_base = {}
    defaults = BASELINE_WORKITEM_ATTR
    for case in cases:
        new_case = {}
        for key in defaults:
            if key in case:
                new_case[key] = case.get(key)
            else:
                new_case[key] = defaults[key][:] if isinstance(defaults[key], list) else defaults[key]

        wi_id = case['polarion']
        new_base[wi_id] = new_case

    with open('base_polarion_new.yaml', 'w') as base_fp:
        yaml.dump(new_base, base_fp)


def load():
    # Load current polarion status
    #current = load_polarion(PROJECT, MANUAL_SPACE)
    #with open('current_polarion.yaml') as polarion_fp:
    #    yaml.dump(current, polarion_fp)

    with open('current_polarion.yaml') as polarion_fp:
        current = yaml.load(polarion_fp)

    # Load linkage configured
    with open('autotest_cases.yaml') as linkage_fp:
        linkage = yaml.load(linkage_fp)

    #check_and_load_automated(current, linkage)
    #check_linkage(current, linkage)

    case_list = check_and_merge_cases(current, linkage)

    check_cases_list(case_list)
    return case_list


def run():
    # Load stage
    all_cases = load()

    #dump_workitem(all_cases)
    update_base(all_cases)


if __name__ == '__main__':
    yaml.add_representer(literal, literal_presenter)
    yaml.add_representer(OrderedDict, ordered_dict_presenter)
    run()
