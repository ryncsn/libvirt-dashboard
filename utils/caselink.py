import requests
from abc import ABCMeta, abstractproperty

CASELINK_URL = 'http://10.66.69.170:8888/caselink/'

class CaseLinkItem():
    __metaclass__ = ABCMeta
    def __init__(self):
        self._caselink_json


    def __getattr__(self, name):
        if not name.startswith('_') and name in self.json:
            # ignore attrs like '_caselink_json', '_json' to avoid recursive getattr.
            return self.json[name]
        raise AttributeError()


    # JSON retrived from caselink, lazy eval.
    @property
    def json(self):
        if hasattr(self, '_caselink_json'):
            return self._caselink_json
        self.refresh()
        return self._caselink_json


    @json.setter
    def json(self, value):
        self._caselink_json = value


    def refresh(self):
        respons = requests.get(self.url)
        #Raise error if anything went wrong.
        respons.raise_for_status()
        self.json = respons.json()


    # Following functions consider caselink stay the same during
    # the life circle of a CaseLinkItem object.
    def __eq__(self, other):
        return self.id == other.id


    def __lt__(self, other):
        return self.id < other.id


    def __hash__(self):
        return self.id


    def __str__(self):
        return self.id

    def __repr__(self):
        return self.__str__()


class AutoCase(CaseLinkItem):
    def __init__(self, case_id):
        self.id = case_id
        self.url = CASELINK_URL + 'auto/' + case_id + '/'


    @property
    def manualcases(self):
        cases = []
        for link in self.json['caselinks']:
            cases.append(ManualCase(link['workitem']))
        return cases


    @property
    def bugs(self):
        bugs = []
        for bug in self.json['bugs']:
            bugs.append(Bug(bug))
        return bugs


class ManualCase(CaseLinkItem):
    def __init__(self, case_id):
        self.id = case_id
        self.url = CASELINK_URL + 'manual/' + case_id + '/'


    @property
    def autocases(self):
        cases = []
        for link in self.json['caselinks']:
            for autocase in link['autocases']:
                cases.append(AutoCase(autocase))
        return cases


    @property
    def bugs(self):
        bugs = []
        for bug in self.json['bugs']:
            bugs.append(Bug(bug))
        return bugs


class Bug(CaseLinkItem):
    def __init__(self, bz_id):
        self.id = bz_id
        self.url = CASELINK_URL + 'bug/' + bz_id + '/'


    @property
    def autocases(self):
        cases = []
        for case in self.json['autocases']:
            cases.append(AutoCase(case))
        return cases


    @property
    def manualcases(self):
        cases = []
        for case in self.json['workitems']:
            cases.append(ManualCase(case))
        return cases


