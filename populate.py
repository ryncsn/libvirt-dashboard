#!/usr/bin/env python

import json
import datetime

from suds.sudsobject import asdict
from pylarion.work_item import _WorkItem

project = 'RedHatEnterpriseLinux7'

members = ('gsun weizhan mzhan tzheng ydu zpeng honzhang dyuan zhwang xuzhang '
           'shyu hliu yanyang juzhou rbian lcheng lhuang pzhang yisun xiaodwan '
           'fjin dzheng hhan qxiao mxie yafu lmen xzhong donwang wzhang fwu '
           'qshen jishao haizhao')

allowed_users = members + ' szacks ci-user'

load_file = 'polarion.base.old'
save_file = 'polarion.base'


def recursive_asdict(d):
    """Convert Suds object into serializable format."""
    out = {}
    for k, v in asdict(d).iteritems():
        if hasattr(v, '__keylist__'):
            out[k] = recursive_asdict(v)
        elif isinstance(v, list):
            out[k] = []
            for item in v:
                if hasattr(item, '__keylist__'):
                    out[k].append(recursive_asdict(item))
                else:
                    out[k].append(item)
        elif isinstance(v, (datetime.datetime, datetime.date)):
            out[k] = str(v)
        else:
            out[k] = v
    return out


def run():
    wis = _WorkItem.query('project.id:%s AND author.id:(%s) AND type:testcase' % (project, members))
    print 'Found %s cases' % len(wis)

    wi_dict = {}
    if load_file:
        with open(load_file) as fp_load:
            wi_dict = json.load(fp_load)

    service = _WorkItem.session.tracker_client.service
    for idx, wi in enumerate(wis):
        print "(%4d/%4d) %s" % (idx+1, len(wis), wi.work_item_id)
        if wi.work_item_id in wi_dict:
            continue

        workitem = service.getWorkItemById(project, wi.work_item_id, [])
        workitem = recursive_asdict(workitem)

        changes = []
        for change in service.generateHistory(wi.uri):
            changes.append(recursive_asdict(change))

        wi_dict[wi.work_item_id] = {
            'workitem': workitem,
            'changes': changes,
        }

        if idx % 100 == 0:
            print 'Saving...'
            with open(save_file, 'w') as fp_save:
                json.dump(wi_dict, fp_save, indent=4)

    print 'Saving...'
    with open(save_file, 'w') as fp_save:
        json.dump(wi_dict, fp_save, indent=4)


if __name__ == '__main__':
    run()
