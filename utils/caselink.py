import requests
from abc import ABCMeta, abstractproperty

CASELINK_URL = 'http://10.66.69.170:8888/caselink/'

class CaselinkCase():
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


class AutoCase(CaselinkCase):
    def __str__(self):
        return self.id


    def __init__(self, case_id):
        self.id = case_id
        self.url = CASELINK_URL + 'auto/' + case_id + '/'


    @property
    def manualcases(self):
        cases = []
        for link in self.caselinks:
            cases.append(link['workitem'])
        return cases


class ManualCase(CaselinkCase):
    def __str__(self):
        return self.id


    def __init__(self, case_id):
        self.id = case_id
        self.url = CASELINK_URL + 'manual/' + case_id + '/'


    @property
    def autocases(self):
        cases = []
        for link in self.caselinks:
            cases += link['autocases']
        return cases
