#!/bin/env python
import sys
import os
import app
import math
import random
import unittest
import datetime
import tempfile
import argparse

import six.moves as sm
from flask import json, jsonify

class randFilledBoolList(list):
    """Generate a List of random booleans, with a given True ratio, and length. """
    def __init__(self, length=10, true_ratio=0.5):
        """TODO: to be defined1. """
        if 0 > true_ratio or 1 < true_ratio:
            raise RuntimeError("true_ratio can only be a number between 1 - 0")
        super(randFilledBoolList, self).__init__()
        for i in sm.range(int(math.floor(length * true_ratio))):
            self.append(True)
        for i in sm.range(int(math.ceil(length * (1 - true_ratio)))):
            self.append(False)
        self = random.shuffle(self)


class DashboardTestCase(unittest.TestCase):
    keep_data = False
    def setUp(self):
        if self.keep_data:
            return self.setUpDev()
        else:
            return self.setUpTest()

    def tearDown(self):
        if self.keep_data:
            return self.tearDownDev()
        else:
            return self.tearDownTest()

    def setUpDev(self):
        self.app = app.app.test_client()
        app.init_db()

    def tearDownDev(self):
        pass

    def setUpTest(self):
        (self.db_fd, self.db_fn) = tempfile.mkstemp()
        app.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + self.db_fn
        app.app.config['TESTING'] = True
        self.app = app.app.test_client()
        app.init_db()

    def tearDownTest(self):
        os.close(self.db_fd)
        os.unlink(self.db_fn)


class EmptyDBTest(DashboardTestCase):
    def test_empty_db(self):
        rv = self.app.get('/api/run/')
        assert b'[]' in rv.data


class FixtureTest(DashboardTestCase):
    fixture_each_group_number = 8
    fixture_group_number = 4
    def submit_test_run(self, **kwargs):
        post_data = {
            "name": "Dev-Test-Run",
            "component": "libvirt",
            "build": "Dev-build",
            "product": "RHEL",
            "version": "7.3",
            "arch": "x86",
            "type": "acceptance",
            "framework": "libvirt-autotest",
            "project": "VIRTTP",
            "date": datetime.datetime.now().isoformat(),
            "ci_url": "http://127.0.0.1:5000",
            "description": "Unit test submission",
            "tags": ["Test", "Fixture"]
        }

        for key, value in kwargs.items():
            post_data[key] = value

        rv = self.app.post('/api/run/', data=post_data);
        rv_data = json.loads(rv.data)
        for key in post_data:
            assert key in rv_data
            if isinstance(post_data[key], list) and isinstance(rv_data[key], list):
                assert set(post_data[key]) == set(rv_data[key])
            else:
                assert post_data[key] == rv_data[key]

        assert "id" in rv_data
        self.last_run_id = str(rv_data.get("id"))

    def submit_case_result(self, name, output, result='passed'):
        post_data = {
            "time": "1.2345",
            "case": name,
        }
        post_data["output"] = output
        if result == 'passed':
            pass
        elif result == 'failed':
            post_data["output"] = output
            post_data["failure"] = output
        elif result == 'skipped':
            post_data["output"] = output
            post_data["skipped"] = output
        else:
            raise RuntimeError()
        rv = self.app.post('/api/run/' + self.last_run_id + "/auto/", data=post_data);
        rv_data = json.loads(rv.data)
        for key in ["time", "case"]:
            assert key in rv_data
            #TODO: Number / String
            assert str(post_data[key]) == str(rv_data[key])

    def submit_a_set_of_test_run(self, run_number, case_prefix=None, **kwargs):
        """
        run_number: how many test run to create
        case_prefix: not used
        kwargs: arg for test run (test suite)
        """
        passed_cases_param = [("a.pass.%s.test", 5), #(<case_name>, <number for each test run>)
                              ("b.pass.%s.test", 3),
                              ("c.pass.%s.test", 3),
                              ("d.pass.%s.test", 3),
                              ("e.pass.%s.test", 3),
                              ("d.missing.%s.test", 3)]

        failed_cases_param = [("b.fail.%s.rare", 1, randFilledBoolList(run_number, 0.9)),
                               #(<case_name>, <number for each test run>,<pass rate>)
                               ("c.fail.%s.sometime", 1, randFilledBoolList(run_number, 0.6)),
                               ("d.fail.%s.often", 1, randFilledBoolList(run_number, 0.2)),
                               ("e.fail.%s.always", 1, randFilledBoolList(run_number, 0))]

        for _ in sm.range(run_number):
            self.submit_test_run(**kwargs)

            for case_name, case_number in passed_cases_param:
                for _number in sm.range(case_number):
                    self.submit_case_result(case_name % _number, "Passed output", "passed")

            for case_name, case_number, case_result_list in failed_cases_param:
                this_case_result = case_result_list.pop()
                for _number in sm.range(case_number):
                    if this_case_result:
                        self.submit_case_result(case_name % _number, "Passed output", "passed")
                    else:
                        self.submit_case_result(case_name % _number, "Failed output", "failed")

    def test_submit_data(self):
        for group_num in sm.range(self.fixture_group_number):
            tags = ["Test %s" % group_num, "Fixture"]
            name = "Dev-Test-Run-%s" % group_num
            build = "Dev-build-%s" % group_num
            self.submit_a_set_of_test_run(self.fixture_each_group_number,
                                          name=name, tags=tags, build=build)


def run():
    parser = argparse.ArgumentParser(description='Unit tests and fixtures for libvirt-dashboard.')
    parser.add_argument('--fixture', dest='fixture', action='store_true',
                        default=False, help=('Generate fixture for test/development then exit.'))
    args = parser.parse_args()

    if args.fixture:
        DashboardTestCase.keep_data = True
        test = FixtureTest("test_submit_data")
        test.debug()
    else:
        unittest.main()
    sys.exit(0)

if __name__ == '__main__':
    run()
