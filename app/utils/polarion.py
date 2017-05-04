"""
More specified ORM for Polaroin
Wrapper for Pylaroin
"""
import logging
import datetime
import tempfile

import os
import sys
import re
import ssl
import traceback

import requests

import xml.etree.ElementTree as ET
import xml.dom.minidom

from config import ActiveConfig
from app import celery

try:
    from pylarion.plan import Plan
    from pylarion.exceptions import PylarionLibException
    PYLARION_INSTALLED = True
except ImportError:
    PYLARION_INSTALLED = False

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s|%(message)s',
    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

COMMIT_CHUNK_SIZE = 100

POLARION_URL = ActiveConfig.POLARION_URL
POLARION_USER = ActiveConfig.POLARION_USER
POLARION_PLANS = ActiveConfig.POLARION_PLANS
POLARION_PROJECT = ActiveConfig.POLARION_PROJECT
POLARION_PASSWORD = ActiveConfig.POLARION_PASSWORD


class PolarionException(Exception):
    pass


def get_nearest_plan_by_pylarion(query, date=None):
    """
    Get next nearest next plan ID
    """
    return "NEAREST PLAN"
    if not date:
        date = datetime.date.today()
    LOGGER.info('Using date %s', date)

    nearest_plan = None
    for plan in Plan.search(query):
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


class TestSuites(object):
    POLARION_PROPERTIES = [
        "polarion-testrun-id",
        "polarion-testrun-template-id",
        "polarion-testrun-status-id",
        "polarion-testrun-template-id",
        "polarion-testrun-title",
        "polarion-testrun-type-id",
        "polarion-dry-run",
        "polarion-include-skipped",
        "polarion-use-testcase-iterations",
        "polarion-lookup-method",
    ]

    def __init__(self, project_id, **kwargs):
        self.properties = {
            "polarion-project-id": project_id,
        }
        self.testsuites = []

    def set_polarion_response(self, response_key, response_value):
        if not response_key.startswith("polarion-response-"):
            response_key = "polarion-response-{}".format(response_key)
        self.properties[response_key] = response_value

    def set_polarion_property(self, key, value):
        if not key.startswith("polarion-"):
            key = "polarion-{}".format(key)
        self.properties[key] = value

    def set_polarion_custom_field(self, key, value):
        if not key.startswith("polarion-custom-"):
            key = "polarion-custom-{}".format(key)
        self.properties[key] = value

    def build_xml_str(self):
        xml_element = ET.Element("testsuites")

        if self.properties:
            props_element = ET.SubElement(xml_element, "properties")
            for k, v in self.properties.items():
                attrs = {'name': str(k), 'value': str(v)}
                ET.SubElement(props_element, "property", attrs)

        for suite in self.testsuites:
            xml_element.append(suite.build_xml_doc())

        xml_string = ET.tostring(xml_element)
        xml_string = TestSuites._clean_illegal_xml_chars(xml_string.decode('utf-8'))
        xml_string = xml.dom.minidom.parseString(xml_string).toprettyxml()

        return xml_string

    @staticmethod
    def _clean_illegal_xml_chars(string_to_clean):
        """
        Removes any illegal unicode characters from the given XML string, Copy & paste code
        """
        # see http://stackoverflow.com/questions/1707890/fast-way-to-filter-illegal-xml-unicode-chars-in-python
        illegal_unichrs = [(0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x84), (0x86, 0x9F),
                           (0xD800, 0xDFFF), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF),
                           (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
                           (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                           (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
                           (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                           (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
                           (0x10FFFE, 0x10FFFF)]

        illegal_ranges = ["%s-%s" % (unichr(low), unichr(high))
                          for (low, high) in illegal_unichrs
                          if low < sys.maxunicode]

        illegal_xml_re = re.compile(u'[%s]' % u''.join(illegal_ranges))
        return illegal_xml_re.sub('', string_to_clean)


class TestSuite(object):
    """
    Contains a set of TestCase object
    """
    def __init__(self, name):
        self.name = name
        self.testcases = []

    def add_testcase(self, testcase):
        assert isinstance(testcase, TestCase)
        self.testcases.append(testcase)

    def build_xml_doc(self):
        xml_element = ET.Element("testsuite", {
            'failures': str(self.failures),
            'errors': str(self.errors),
            'skipped': str(self.skipped),
            'tests': str(len(self.testcases)),
            'time': str(self.time),
            'name': str(self.name)
        })

        for testcase in self.testcases:
            xml_element.append(testcase.build_xml_doc())

        return xml_element

    @property
    def failures(self):
        return len([c for c in self.testcases if c.failure])

    @property
    def errors(self):
        return len([c for c in self.testcases if c.error])

    @property
    def skipped(self):
        return len([c for c in self.testcases if c.skipped])

    @property
    def time(self):
        return sum([c.elapsed_sec for c in self.testcases])


class TestCase(object):
    """
    Stands for a record of a test run on Polarion
    """
    def __init__(self, name, id,
                 stdout=None, stderr=None,
                 failure=None, skipped=None, error=None,
                 classname=None, comment=None, elapsed_sec=None):
        # Attr
        self.classname = classname
        self.name = name

        # Sub ele
        self.stdout = stdout
        self.stderr = stderr
        self.failure = failure
        self.skipped = skipped
        self.error = error
        self.elapsed_sec = elapsed_sec

        # Polarion Prop
        self.properties = {
            "polarion-testcase-id": id,
            "polarion-testcase-comment": comment,
        }

    def set_polarion_parameter(self, key, value):
        if not key.startswith("polarion-parameter-"):
            key = "polarion-parameter-{}".format(key)
        self.properties[key] = value

    @property
    def passed(self):
        return not self.failure and not self.skipped and not self.error

    def build_xml_doc(self):
        status = iter([self.failure, self.skipped, self.error])
        assert self.passed or any(status) and not any(status)

        attrs = {"name": str(self.name)}
        if self.classname:
            attrs["classname"] = str(self.classname)
        if self.elapsed_sec:
            attrs["time"] = str(self.elapsed_sec)

        xml_element = ET.Element("testcase", attrs)

        if self.failure:
            ET.SubElement(xml_element, "failure", {"type": "failure", "message": str(self.failure)})

        if self.skipped:
            ET.SubElement(xml_element, "skipped", {"type": "skipped", "message": str(self.skipped)})

        if self.error:
            ET.SubElement(xml_element, "error", {"type": "error", "message": str(self.error)})

        ET.SubElement(xml_element, "system-out").text = str(self.stdout or "")
        ET.SubElement(xml_element, "system-err").text = str(self.stderr or "")

        if self.properties:
            props_element = ET.SubElement(xml_element, "properties")
            for k, v in self.properties.items():
                attrs = {'name': str(k), 'value': str(v)}
                ET.SubElement(props_element, "property", attrs)

        return xml_element


# pylint: disable=no-member
class TestRunRecord(object):
    def __init__(self, project_id, testrun_name, **kwargs):
        self.tss = TestSuites(project_id)

        self.set_polarion_property = self.tss.set_polarion_property
        self.set_polarion_response = self.tss.set_polarion_response
        self.set_polarion_custom_field = self.tss.set_polarion_custom_field

        for key, value in kwargs.items():
            self.tss.set_polarion_custom_field(key, value)

        self.ts = TestSuite(testrun_name)
        self.tss.testsuites.append(self.ts)

    def get_polarion_property(self, key):
        if not key.startswith("polarion-"):
            key = "polarion-{}".format(key)
        return self.tss.properties[key]

    def add_testcase(
            self, case, result, elapsed_sec, comment=None):
        """
        Update test run content according to the test cases.
        """

        if result not in ['failed', 'passed', 'blocked']:
            raise PolarionException('Result can only be "failed", "passed" or "blocked"')

        # executed/executed_by is set automatically to the submit user and submit time
        record = TestCase(
            case, case, elapsed_sec=elapsed_sec, comment=comment
        )

        self.ts.add_testcase(record)
        return record

    def submit(self):
        """
        Submit / Update a test run on polarion.
        """
        xmldoc = self.tss.build_xml_str()
        fd, temp_path = tempfile.mkstemp()

        with open(temp_path, "w") as fp:
            fp.write(xmldoc)

        with open(temp_path, "w") as fp:
            requests.post("{}/import/xunit".format(POLARION_URL),
                          auth=(POLARION_USER, POLARION_PASSWORD),
                          files={"temp_path": fp})

        os.close(fd)
