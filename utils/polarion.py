import logging
import sys
import datetime
import time
import os
import re
import ssl

from collections import OrderedDict

from pylarion.document import Document
from pylarion.work_item import TestCase
from pylarion.test_run import TestRun
from pylarion.plan import Plan


COMMIT_SIZE = 100
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s|%(message)s',
    level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def get_nearest_plan(version):
    """
    Get next nearest next plan ID
    """
    today = datetime.date.today()
    LOGGER.info('Today is %s', today)

    nearest_plan = None
    for plan in Plan.search(version):
        LOGGER.info('Found plan %s, due date %s', plan.name, plan.due_date)
        if not plan.due_date:
            continue
        if today < plan.due_date:
            if not nearest_plan or plan.due_date < nearest_plan.due_date:
                nearest_plan = plan

    LOGGER.info('Next nearest plan is %s', nearest_plan.name)
    return nearest_plan.plan_id


class TestRunSession():
    def __init__(self):
        pass

    def __enter__(self):
        self.session = TestCase.session
        self.session.tx_begin()
        return self.session

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type:
            print exception_type
            print exception_value
            print traceback
        else:
            try:
                self.session.tx_commit()
            except ssl.SSLError as detail:
                logging.warning(detail)


class TestRunRecord():
    def __init__(self, project=None, name=None, description=None,
                 type=None, build=None, version=None, arch=None, date=None):

        self.project = project
        self.name = name
        self.type = type
        self.date = date
        self.build = build
        self.version = version
        self.arch = arch
        self.description = description

        self.records = []
        self.query = (('project.id:%s AND type:testcase ' % (self.project)
                       + 'AND (%s)'))

    def add_record(self, case=None, result=None, duration=None, datetime=None, executed_by=None, comment=None):
        """
        Update test run content according to the test cases.
        """

        if result not in ['failed', 'passed']:
            raise RuntimeError('Result can only be "failed" or "passed"')

        LOGGER.info('Creating Test Record for %s', case)

        record = Record(
            case=case,
            #factory=self.client.factory,
            project=self.project,
            duration=duration,
            executed=datetime,
            executed_by=executed_by,
            result=result,
            comment=comment,
        )

        self.records.append(record)

    def fake_submit(self):
        #print get_nearest_plan(self.version):
        tr_name = '%s %s %s %s %s %s' % (
            self.name, self.type, self.build, self.version, self.arch,
            self.date.strftime('%Y-%m-%d %H-%M-%S'))
        # Replace unsupported characters
        tr_name = re.sub(r'[.\/:*"<>|~!@#$?%^&\'*()+`,=]', '-', tr_name)
        print tr_name
        query = self.query % " OR ".join(["id:%s" % rec.case for rec in self.records])
        print query

        for idx, record in enumerate(self.records):
            record.fake_polarion_object()

    def submit(self, session=None):
        self.session = session
        if not self.session:
            raise RuntimeError('Need to start a session.')

        tr_name = '%s %s %s %s %s %s' % (
            self.name, self.type, self.build, self.version, self.arch,
            self.date.strftime('%Y-%m-%d %H-%M-%S'))
        # Replace unsupported characters
        tr_name = re.sub(r'[.\/:*"<>|~!@#$?%^&\'*()+`,=]', '-', tr_name)

        test_run = TestRun.create(
            self.project, tr_name, 'libvirt-autotest',
            #plannedin=get_nearest_plan(self.version)
        )
        test_run.description = self.description
        test_run.group_id = self.build
        # [manualSelection, staticQueryResult, dynamicQueryResult, staticLiveDoc,
        #  dynamicLiveDoc, automatedProcess]
        test_run.select_test_cases_by = 'staticQueryResult'
        test_run.query = self.query % " OR ".join(["id:%s" % rec.case for rec in self.records])
        self.session.tx_commit()
        self.session.tx_begin()

        self.client = self.session.test_management_client
        for idx, record in enumerate(self.records):
            self.client.service.addTestRecordToTestRun(test_run.uri,
                                                       record.get_polarion_object(self.client.factory))
        try:
            session.tx_commit()
        except ssl.SSLError as detail:
            logging.warning(detail)
        self.session.tx_begin()

        test_run.status = 'finished'
        LOGGER.info('Updating Test Run')
        test_run.update()
        try:
            session.tx_commit()
        except ssl.SSLError as detail:
            logging.warning(detail)
        self.session.tx_begin()


class Record():
    def __init__(self, case=None, project=None, duration=None, executed=None,
                 executed_by=None, result=None, comment=None):
        self.case = case
        self.project = project
        self.duration = duration
        self.executed = executed
        self.executed_by = executed_by
        self.result = result
        self.comment = comment

    def fake_polarion_object(self):
        print ("subterra:data-service:objects:/default/"
               "%s${WorkItem}%s" %
               (self.project, self.case))
        print self.duration
        print self.executed
        print self.result
        print self.comment
        print ("subterra:data-service:objects:/default/"
               "${User}%s" % self.executed_by)

    def get_polarion_object(self, factory=None):
        """
        Submit a test to polarion
        """
        self.factory = factory
        if not self.factory:
            raise RuntimeError()

        if hasattr(self, '_polarion_object'):
            return self._polarion_object

        suds_object = self.factory.create('tns3:TestRecord')

        suds_object.testCaseURI = ("subterra:data-service:objects:/default/"
                                   "%s${WorkItem}%s" %
                                   (self.project, self.case))
        suds_object.duration = self.duration
        suds_object.executed = self.executed

        result_obj = self.factory.create('tns4:EnumOptionId')
        result_obj.id = self.result
        suds_object.result = result_obj

        if self.comment is not None:
            comment_obj = self.factory.create('tns2:Text')
            comment_obj.type = "text/html"
            comment_obj.content = '<pre>%s</pre>' % self.comment
            comment_obj.contentLossy = False
            suds_object.comment = comment_obj

        suds_object.executedByURI = ("subterra:data-service:objects:/default/"
                                     "${User}%s" % self.executed_by)
        self._polarion_object = suds_object
        return suds_object
