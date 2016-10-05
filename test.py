#!/bin/env python
import sys
import os
import app
import unittest
import tempfile
import argparse

from flask import json, jsonify

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
    def submit_test_run(self):
        post_data = {
            "name": "libvirt-RHEL-7.3-runtest-x86_64-acceptance-general",
            "component": "libvirt",
            "build": "2.0.1",
            "product": "RHEL",
            "version": "7.3",
            "arch": "x86",
            "type": "acceptance",
            "framework": "libvirt-autotest",
            "project": "VIRTTP",
            "date": "2016-07-18T17:02:28.798848",
            "ci_url": "http://127.0.0.1:5000",
            "description": "Unit test submission",
        }

        rv = self.app.post('/api/run/', data=post_data);
        rv_data = json.loads(rv.data)
        for key in post_data:
            assert key in rv_data
            assert post_data[key] == rv_data[key]

        assert "id" in rv_data
        self.run_id = str(rv_data.get("id"))

    def submit_auto_success_result(self, name):
        post_data = {
            "output": "OUTPUT CONTENT",
            "time": "1.345",
            "case": name,
        }
        rv = self.app.post('/api/run/' + self.run_id + "/auto/", data=post_data);
        rv_data = json.loads(rv.data)
        for key in ["time", "case"]:
            assert key in rv_data
            #TODO: Number / String
            assert str(post_data[key]) == str(rv_data[key])

    def submit_auto_failed_result(self, name, failure):
        post_data = {
            "output": "OUTPUT CONTENT",
            "time": "1.345",
            "case": name,
            "failure": failure
        }
        rv = self.app.post('/api/run/' + self.run_id + "/auto/", data=post_data);
        rv_data = json.loads(rv.data)
        for key in ["time", "case"]:
            assert key in rv_data
            assert str(post_data[key]) == str(rv_data[key])

    def test_submit_data(self):
        self.submit_test_run()
        for case in ["a.b.c.d",
                     "a.b.c.4.e",
                     "a.b.c.3.e",
                     "a.b.c.2.e",
                     "a.b.c.1.e",
                     "a.b.c.4.f",
                     "a.b.c.3.f",
                     "a.b.c.2.f",
                     "a.b.c.1.f",
                     "1.3.4"]:
            self.submit_auto_success_result(case)

        for failure, case in [
            ("Failure 1", "1.1.1"),
            ("Failure 2", "1.2.1"),
            ("Failure 2", "1.2.2"),
            ("Failure 2", "1.2.3"),
            ("Failure 2", "1.2.4"),
            ("Failure 3", "1.3.1"),
            ("Failure 3", "1.3.2"),
            ("Failure 3", "1.3.3"),
            ("Failure UnKnown", "1.4.1")]:
            self.submit_auto_failed_result(case, failure)

    def runTest(self):
        return self.test_submit_data()


def run():
    parser = argparse.ArgumentParser(description='Unit tests and fixtures for libvirt-dashboard.')
    parser.add_argument('--fixture', dest='fixture', action='store_true',
                        default=False, help=('Generate fixture for test/development then exit.'))
    args = parser.parse_args()

    if args.fixture:
        DashboardTestCase.keep_data = True
        test = FixtureTest()
        test.debug()
    else:
        unittest.main()
    sys.exit(0)

if __name__ == '__main__':
    run()
