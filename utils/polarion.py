"""
More specified ORM for Polaroin
Wrapper for Pylaroin
"""
import logging
import datetime
import re
import ssl
import threading

from pylarion.base_polarion import BasePolarion
from pylarion.document import Document
from pylarion.work_item import TestCase
from pylarion.test_run import TestRun
from pylarion.plan import Plan
from pylarion.exceptions import PylarionLibException
from pylarion.text import Text

from httplib import HTTPException
from suds import WebFault
from ssl import SSLError
from pylarion.exceptions import PylarionLibException

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s|%(message)s',
    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

COMMIT_CHUNK_SIZE = 100


class PolarionException(Exception):
    pass


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

    if nearest_plan:
        LOGGER.info('Next nearest plan is %s', nearest_plan.name)
        return nearest_plan.plan_id
    else:
        raise PolarionException("Unable to find a planned in.")


class PolarionSession(object):
    """
    Manage session, allow tx_commit during session
    """
    lock = threading.RLock()
    def __enter__(self):
        self.lock.acquire()
        self.session = BasePolarion.session
        self.session._reauth()
        if not self.session.tx_in():
            self.session.tx_begin()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            if exception_type:
                LOGGER.error("Got exception: %s \n %s \n %s",
                             exception_type, exception_value, traceback)
                self.session.tx_rollback()
            else:
                try:
                    if self.session.tx_in():
                        self.session.tx_commit()
                    self.session.tx_release()
                    self.session._logout()
                except ssl.SSLError as detail:
                    LOGGER.error(detail)
        finally:
            self.lock.release()

    def reauth(self):
        self.session._reauth()
        self.commit()

    def commit(self):
        if self.session.tx_in():
            try:
                self.session.tx_commit()
            except ssl.SSLError as detail:
                LOGGER.error(detail)
        self.session.tx_begin()

    def __getattr__(self, attr):
        return getattr(self.session, attr)


# pylint: disable=no-member
class TestRunRecord(object):
    # TODO: dashboard_id not used
    __props__ = ("dashboard_id", "name", "component", "build",
                 "product", "version", "arch", "type",
                 "framework", "project", "date", "ci_url",
                 "title_tags", "polarion_tags", "description")

    def __init__(self, **kwargs):
        for prop in self.__props__:
            setattr(self, prop, kwargs.pop(prop))

        self._test_run = None
        self.records = []
        self.query = (('project.id:%s AND type:testcase ' % (self.project)
                       + 'AND (%s)'))

        self.test_run_id = '%s %s %s %s' % (
            self.name, self.framework, self.build,
            self.date.strftime('%Y-%m-%d %H-%M-%S')
        )

        if self.title_tags:
            self.test_run_id += ' %s' % (' '.join(self.title_tags))

        # Replace unsupported characters
        self.test_run_id = re.sub(r'[.\/:*"<>|~!@#$?%^&\'*()+`,=]', '-', self.test_run_id)

        # TODO: tempalte name
        self.template_name = "libvirt-autotest"

    def add_record(self, case=None, result=None, duration=None,
                   record_datetime=None, executed_by=None, comment=None):
        """
        Update test run content according to the test cases.
        """

        if result not in ['failed', 'passed', 'blocked']:
            raise PolarionException('Result can only be "failed", "passed" of "blocked"')

        LOGGER.debug('Creating Test Record for %s', case)

        record = Record(
            case=case,
            #factory=self.client.factory,
            project=self.project,
            duration=duration,
            executed=record_datetime,
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

    def _set_jenkinsjobs(self, url=None):
        """
        Hacky way to set jenkinsjobs.
        """
        if not self._test_run or url is None:
            return None

        # Make sure jenkinsjobs field exists.
        self._test_run._set_custom_field("jenkinsjobs", "")

        for cf in self._test_run._suds_object.customFields[0]:
            if cf.key == "jenkinsjobs":
                cf.value = Text(url)._suds_object
                cf.value.type = "text/plain"

    def _set_tags(self, tags):
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
        self._test_run.query = self.query % " OR ".join(
            ["id:%s" % rec.case for rec in self.records])
        self._set_jenkinsjobs(self.ci_url)
        self._set_tags(self.polarion_tags)

    def submit(self, session):
        """
        Submit / Update a test run on polarion.
        """
        def _retry_wrapper(func, times=10):
            for retry in reversed(range(times)):
                try:
                    func()
                except (WebFault, SSLError) as error:
                    if "timed out" in error.message and retry:
                        LOGGER.info("Request timeout, retry left %s", retry)
                        session.commit()
                        continue
                    elif "Not authorized" in error.message and retry:
                        LOGGER.info("Auth expired, retry left %s", retry)
                        session.reauth()
                        continue
                    else:
                        return error
                except HTTPException as error:
                    if retry:
                        LOGGER.info("HTTP error %s, retry lift %s", error, retry)
                        session.reauth()
                        continue
                    else:
                        return error
            return None

        try:
            self._test_run = TestRun(self.test_run_id, project_id=self.project)
            LOGGER.info('Updating Test Run')
        except PylarionLibException as error:
            if "not found" in error.message:
                self._create_on_polarion()
                LOGGER.info('Empty Test Run Created')
        else:
            LOGGER.info('Test Run Founded')

        # Set meta data.
        self._update_info_on_polarion()
        session.commit()
        LOGGER.info('Test Run Metadata Updated')

        # Add test run records.
        client = session.test_management_client
        for idx, record in enumerate(self.records):
            LOGGER.info('Uploading Record %s', idx)
            error = _retry_wrapper(lambda: client.service.addTestRecordToTestRun(self._test_run.uri,
                                                                                 record.gen_polarion_object(client.factory)))
            if error:
                raise PolarionException("Failed during creating test record %s" % error)

        LOGGER.info('Test Run Records Added')
        self._test_run.status = 'finished'
        if not _retry_wrapper(lambda: self._test_run.update(), 30):
            raise PolarionException("Failed saving test record %s" % error)
        LOGGER.info('Submit Done')


class Record(object):
    __props__ = ("case", "project", "duration", "executed",
                 "executed_by", "result", "comment")

    def __init__(self, **kwargs):
        for prop in self.__props__:
            setattr(self, prop, kwargs.pop(prop))

        self._polarion_object = None

    def gen_polarion_object(self, factory):
        """
        Generate a Test Run Record object for Polarion.
        """

        if self._polarion_object is not None:
            return self._polarion_object

        suds_object = factory.create('tns3:TestRecord')

        suds_object.testCaseURI = ("subterra:data-service:objects:/default/"
                                   "%s${WorkItem}%s" %
                                   (self.project, self.case))
        suds_object.duration = self.duration
        suds_object.executed = self.executed

        result_obj = factory.create('tns4:EnumOptionId')
        result_obj.id = self.result
        suds_object.result = result_obj

        if self.comment is not None:
            comment_obj = factory.create('tns2:Text')
            comment_obj.type = "text/html"
            comment_obj.content = '<pre>%s</pre>' % self.comment
            comment_obj.contentLossy = False
            suds_object.comment = comment_obj

        suds_object.executedByURI = ("subterra:data-service:objects:/default/"
                                     "${User}%s" % self.executed_by)
        self._polarion_object = suds_object
        return suds_object
