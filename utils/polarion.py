"""
More specified ORM for Polaroin
Wrapper for Pylaroin
"""
import logging
import sys
import datetime
import time
import os
import re
import ssl

from collections import OrderedDict

from pylarion.base_polarion import BasePolarion
from pylarion.document import Document
from pylarion.work_item import TestCase
from pylarion.test_run import TestRun
from pylarion.plan import Plan
from pylarion.exceptions import PylarionLibException


COMMIT_SIZE = 100
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s|%(message)s',
    level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def get_nearest_plan(version, date=None):
    """
    Get next nearest next plan ID
    """
    if not date:
        date = datetime.date.today()
    LOGGER.info('Using date %s', date)

    nearest_plan = None
    for plan in Plan.search(version):
        LOGGER.info('Found plan %s, due date %s', plan.name, plan.due_date)
        if not plan.due_date:
            continue
        if date < plan.due_date:
            if not nearest_plan or plan.due_date < nearest_plan.due_date:
                nearest_plan = plan

    LOGGER.info('Next nearest plan is %s', nearest_plan.name)
    return nearest_plan.plan_id


class PolarionSession():
    """
    Manage session, allow tx_commit during session
    """
    def __init__(self):
        pass

    def __enter__(self):
        self.session = BasePolarion.session
        self.session.tx_begin()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type:
            LOGGER.error("Got exception:")
            LOGGER.error(str(exception_type))
            LOGGER.error(str(exception_value))
            LOGGER.error(str(traceback))
            self.session.tx_rollback()
        else:
            try:
                self.session.tx_commit()
                self.session.tx_release()
            except ssl.SSLError as detail:
                logging.warning(detail)

    def commit(self):
        if self.session.tx_in():
            try:
                self.session.tx_commit()
            except ssl.SSLError as detail:
                logging.warning(detail)
        self.session.tx_begin()

    def __getattr__(self, attr):
        return getattr(self.session, attr)


class TestRunRecord():
    def __init__(self, project=None, name=None, description=None,
                 type=None, build=None, version=None, arch=None, date=None, tags=None):

        self.project = project
        self.name = name
        self.type = type
        self.date = date # datetime
        self.build = build
        self.version = version
        self.arch = arch
        self.description = description
        self.tags = tags

        self.records = []

        self.query = (('project.id:%s AND type:testcase ' % (self.project)
                       + 'AND (%s)'))

        # TODO: better test_run_id handling
        self.test_run_id = '%s %s %s %s %s %s' % (
            self.name, self.type, self.build, self.version, self.arch,
            self.date.strftime('%Y-%m-%d %H-%M-%S')
        )
        # Replace unsupported characters
        self.test_run_id = re.sub(r'[.\/:*"<>|~!@#$?%^&\'*()+`,=]', '-', self.test_run_id)

        # TODO: tempalte name
        self.template_name = "libvirt-autotest"

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

    def _create_on_polarion(self):
        """
        Create a empty Test Run with test_run_id on Polarion
        """
        self._test_run = TestRun.create(
            self.project, self.test_run_id, self.template_name,
            plannedin=get_nearest_plan(self.version, self.date.date()), assignee='kasong'
        )
        self.session.commit()

    def _set_tags(self, tags=None):
        """
        Hacky way to set tags.
        """
        if not self._test_run or tags is None:
            return None

        # Make sure tags field exists.
        self._test_run._set_custom_field("tags", "")

        for cf in self._test_run._suds_object.customFields[0]:
            if cf.key == "tags":
                cf.value = tags

    def _update_info_on_polarion(self):
        """
        Update Test Run info on Polarion
        """
        self._test_run.description = self.description
        self._test_run.group_id = self.build
        # [manualSelection, staticQueryResult, dynamicQueryResult, staticLiveDoc,
        #  dynamicLiveDoc, automatedProcess]
        self._test_run.select_test_cases_by = 'staticQueryResult'
        self._test_run.query = self.query % " OR ".join(["id:%s" % rec.case for rec in self.records])
        self._set_tags(self.tags)

    def submit(self, session=None):
        """
        Submit / Update a test run on polarion.
        """
        # TODO: update a test run cause duplicated Test records.
        self.session = session
        if not self.session:
            raise RuntimeError('Need to start a session.')

        try:
            self._test_run = TestRun(self.test_run_id, project_id=self.project)
            LOGGER.info('Updating Test Run')
        except PylarionLibException as e:
            if "not found" in e.message:
                self._create_on_polarion()
                LOGGER.info('Created Test Run')

        # Set meta data.
        self._update_info_on_polarion()

        # Add test run records.
        self.client = self.session.test_management_client
        for idx, record in enumerate(self.records):
            self.client.service.addTestRecordToTestRun(self._test_run.uri,
                                                       record.gen_polarion_object(self.client.factory))

        # Mark Finished
        self._test_run.status = 'finished'

        # Submit
        self._test_run.update()
        self.session.commit()


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

    def gen_polarion_object(self, factory=None):
        """
        Generate a Test Run Record object for Polarion.
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
