import requests
from abc import ABCMeta, abstractproperty
from flask import current_app

CASELINK_URL = 'http://127.0.0.1:8888/'

def lazy_property(fn):
    lazy_name = '__lazy__' + fn.__name__
    @property
    def lazy_eval(self):
        if not hasattr(self, lazy_name):
            setattr(self, lazy_name, fn(self))
        return getattr(self, lazy_name)
    return lazy_eval


class CaseLinkItem():
    """
    Base Class for all Caselink Item
    """
    __metaclass__ = ABCMeta

    @abstractproperty
    def url(self):
        pass

    @abstractproperty
    def id(self):
        pass

    def __init__(self):
        pass

    @property
    def json(self):
        if hasattr(self, '__caselink__json'):
            return getattr(self, '__caselink__json')
        else:
            if self.exists():
                return getattr(self, '__caselink__json')
            else:
                setattr(self, '__caselink__json', {})
                return getattr(self, '__caselink__json')

    @json.setter
    def json(self, value):
        setattr(self, '__caselink__json', value)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError('No atrribute: ' + str(name))
        if not name in self.json:
            raise AttributeError('No atrribute: ' + str(name))
        return self.json[name]

    @classmethod
    def create(cls, id, **kwargs):
        json = kwargs
        json['id'] = id
        res = requests.post(cls.base_url, json=json)

        #TODO
        #if res.json()['non_field_errors']:
        #    return cls(res.json()['id'])

        res.raise_for_status()

        return cls(res.json()['id'])

    def refresh(self):
        """
        Refetch info from caselink, remove all cached properties.
        """
        respons = requests.get(self.url)
        #Raise error if anything went wrong.
        respons.raise_for_status()
        self.json = respons.json()
        for attr, value in self.__dict__.iteritems():
            if attr.startswith('__lazy__'):
                delattr(self, attr)
        return self

    def exists(self):
        if hasattr(self, '__caselink__json'):
            return True
        try:
            self.refresh()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False
            else:
                raise e
        return True

    def save(self):
        if self.exists():
            requests.put(self.url, self.json)
        else:
            if hasattr(self, '__caselink__json'):
                requests.post(self.url, json=self.json)
        self.refresh()

    def delete(self):
        if self.exists():
            requests.delete(self.url)
        else:
            raise RuntimeError()

    # Following functions consider caselink stay the same during
    # the life circle of a CaseLinkItem object.
    def __eq__(self, other):
        if not isinstance(other, CaseLinkItem):
            return False
        return self.url == other.url

    def __lt__(self, other):
        return self.url < other.url

    def __hash__(self):
        return self.url

    def __str__(self):
        return "<CaselinkItem " + str(self.id) + ">"

    def __repr__(self):
        return self.__str__()


class AutoCase(CaseLinkItem):
    base_url = CASELINK_URL + 'auto/'
    def __init__(self, case_id):
        self._id = str(case_id)
        self._url = self.base_url + str(case_id) + '/'

    def __str__(self):
        return "<AutoCase " + str(self.id) + ">"

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def linkages(self):
        caselinks = []
        for link in self.json['caselinks']:
            caselinks.append(Linkage(link))
        return caselinks

    @linkages.setter
    def linkages_setter(self, manualcases):
        raise RuntimeError("Please Use Linkage.create to create linkage.")

    @lazy_property
    def manualcases(self):
        cases = []
        for link in [Linkage(link_id) for link_id in self.json['caselinks']]:
            cases.append(ManualCase(link.workitem))
        return cases

    @manualcases.setter
    def manualcases_setter(self, manualcases):
        raise RuntimeError("Please Use Linkage.create to create linkage.")

    @lazy_property
    def bugs(self):
        bugs = []
        for bug in self.json['bugs']:
            bugs.append(Bug(bug))
        return bugs

    @bugs.setter
    def bugs_setter(self, manualcases):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")

    @lazy_property
    def failures(self):
        failures = []
        for failure in self.json['failures']:
            failures.append(AutoCaseFailure(failure))
        return failures

    @failures.setter
    def failures_setter(self, manualcases):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")


class ManualCase(CaseLinkItem):
    base_url = CASELINK_URL + 'manual/'
    def __init__(self, case_id):
        self._id = str(case_id)
        self._url = self.base_url + str(case_id) + '/'

    def __str__(self):
        return "<ManualCase " + str(self.id) + ">"

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def linkages(self):
        caselinks = []
        for link in self.json['caselinks']:
            caselinks.append(Linkage(link))
        return caselinks

    @linkages.setter
    def linkages_setter(self, manualcases):
        raise RuntimeError("Please Use Linkage.create to create linkage.")

    @lazy_property
    def autocases(self):
        cases = []
        for link in [Linkage(link_id) for link_id in self.json['caselinks']]:
            for autocase in link.autocases:
                cases.append(AutoCase(autocase))
        return cases

    @lazy_property
    def bugs(self):
        bugs = []
        for bug in self.json['bugs']:
            bugs.append(Bug(bug))
        return bugs


class Bug(CaseLinkItem):
    base_url = CASELINK_URL + 'bug/'
    def __init__(self, bz_id):
        self._id = str(bz_id)
        self._url = base_url + str(bz_id) + '/'

    def __str__(self):
        return "<Bug " + str(self.id) + ">"

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._id

    @lazy_property
    def autocases(self):
        cases = []
        for case in self.json['autocases']:
            cases.append(AutoCase(case))
        return cases

    @autocases.setter
    def autocase_setter(self, autocases):
        raise RuntimeError("Please Use AutoCase Pattern to Link autocases.")

    @lazy_property
    def manualcases(self):
        cases = []
        for case in self.json['manualcases']:
            cases.append(ManualCase(case))
        return cases


class AutoCaseFailure(CaseLinkItem):
    unique_together = ("failure_regex", "autocase_pattern",)
    base_url = CASELINK_URL + 'failure/'

    def __init__(self, id):
        """
        Failures uses a surrogate key
        """
        self._id = str(id)
        self._url = self.base_url + str(id) + '/'

    def __str__(self):
        return "<Failure " + str(self.id) + ">"

    @classmethod
    def create(cls, failure_regex, autocase_pattern, failure_type=None, bug=None):
        if failure_type not in ['BUG', 'CASE-UPDATE']:
            raise RuntimeError()
        if failure_type == 'BUG' and not bug:
            raise RuntimeError()

        res = requests.post(cls.base_url, json={
            'failure_regex': failure_regex,
            'autocase_pattern': autocase_pattern,
            'type': failure_type,
            'bug': bug,
        })

        #TODO
        #if res.json()['non_field_errors']:
        #    return cls(res.json()['id'])

        res.raise_for_status()

        return cls(res.json()['id'])

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url

    @lazy_property
    def bug(self):
        return Bug(self.json['bug'])

    @lazy_property
    def manualcases(self):
        cases = []
        for case in self.bug.manualcases:
            cases.append(ManualCase(case.id))
        return cases


class Linkage(CaseLinkItem):
    unique_together = ("workitem", "autocase_pattern",)
    base_url = CASELINK_URL + 'link/'

    def __init__(self, id):
        """
        Linkage uses a surrogate key
        """
        self._id = str(id)
        self._url = self.base_url + str(id) + '/'

    def __str__(self):
        return "<Linkage workitem:" + str(self.workitem) + " pattern: " + str(self.autocase_pattern) + ">"

    @classmethod
    def create(cls, workitem, autocase_pattern):
        res = requests.post(cls.base_url, json={
            'workitem': workitem,
            'autocase_pattern': autocase_pattern,
        })

        #if res.json()['non_field_errors']:
        #    return cls(res.json()['id'])

        res.raise_for_status()

        return cls(res.json()['id'])

    @property
    def id(self):
        return self._id

    @property
    def url(self):
        return self._url
