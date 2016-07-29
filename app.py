#!/usr/bin/env python

from flask import Flask, request, Markup
from flask import render_template, make_response, jsonify
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_restful import Resource, Api, reqparse, inputs
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from requests import HTTPError

import json

import re

import utils.caselink as CaseLink
import utils.polarion as Polarion

app = Flask(__name__)
app.config.from_object('config.ActiveConfig')

db = SQLAlchemy(app)
from model import *

api = Api(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@app.template_filter('nl2br_simple')
def nl2br_simple(s):
    s = s.replace('\\n', ';')
    return Markup(s)

def bootstrap():
    db.create_all()


TestRunParser = reqparse.RequestParser(bundle_errors=True)
TestRunParser.add_argument('arch', required=True)
TestRunParser.add_argument('type', required=True)
TestRunParser.add_argument('name', required=True)
TestRunParser.add_argument('date', type=inputs.datetime_from_iso8601, required=True)
TestRunParser.add_argument('build', required=None)
TestRunParser.add_argument('project', required=True)
TestRunParser.add_argument('version', required=True)
TestRunParser.add_argument('component', required=True)
TestRunParser.add_argument('framework', required=None)
TestRunParser.add_argument('description', default=None)


CaseResultParser = reqparse.RequestParser(bundle_errors=True)
CaseResultParser.add_argument('case', required=True)
CaseResultParser.add_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=True)
CaseResultParser.add_argument('output', required=True)
CaseResultParser.add_argument('failure', default=None)
CaseResultParser.add_argument('skip', default=None)
CaseResultParser.add_argument('bugs', default=None)
CaseResultParser.add_argument('error', default=None)
CaseResultParser.add_argument('manualcases', default=None)
CaseResultParser.add_argument('source', default='')

CaseResultUpdateParser = CaseResultParser.copy()
CaseResultUpdateParser.replace_argument('output', required=False)
CaseResultUpdateParser.replace_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=False)
CaseResultUpdateParser.replace_argument('case', required=False)


def column_to_table(model, data, code, extra_column=[]):
    """
    Render array of entrys of a database with datatable.
    Array should contain dicts with the same keys.
    """
    columns = model.__table__.columns
    columns = [str(col).split('.')[-1] for col in columns]
    columns += extra_column
    resp = make_response(render_template('column2table.html',
                                         column_names=columns,
                                         column_datas=columns,
                                         data=data), 200)
    return resp


class TestRunList(Resource):
    def get(self):
        runs = Run.query.all()
        ret = []
        for run in runs:
            ret.append(run.as_dict())
        return ret

    def post(self):
        args = TestRunParser.parse_args()
        run = args
        run['submitted'] = False
        run = Run(**args)
        db.session.add(run)
        try:
            db.session.commit()
        except IntegrityError as e:
            if "UNIQUE constraint failed" in  e.message:
                return make_response("Already exists.", 400)
            else:
                raise e
        return run.as_dict()


class TestRunDetail(Resource):
    def get(self, run_id):
        args = TestRunParser.parse_args()
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        return ret.as_dict

    def put(self, run_id):
        args = TestRunParser.parse_args()
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        for key in args.keys():
            run[key] = args[key]
        db.session.add(run)
        db.session.commit()
        return run, 201


def check_test_result(result, session):
    """
    Take a unsaved result instance,
    Check with other results in database and caselink.

    'result' should only have attribute 'case', 'output',
    and one of 'failure', 'skip', other attributes will be genereted.
    """
    try:
        this_autocase = CaseLink.AutoCase(result.case)
    except HTTPError as e:
        if e.response.status_code == 404:
            return {'message': 'Auto case not included in caselink'}, 400
        else:
            return {'message': 'Caselink didn\'t response in a expected way'}, 400

    # Failed -> look up in failures, if any bug matches, mark manualcase failed
    # Passed -> look up in linkages(manualcases), if all related autocase of a manualcase
    #           passed, mark the manualcase passed

    # Mark error when lookup failed

    # First, generate attributes for this result instance only.
    result.bugs = ''
    result.manualcases = ''
    result.error = ''

    if result.failure:
        # Auto Case failed with message <result.failure>
        NoMatchingFailure = True
        for failure in this_autocase.failures:
            if re.match(failure.failure_regex, result.failure) is not None:
                NoMatchingFailure = False
                # From caselink
                bug = failure.bug.id
                if bug not in result.bugs:
                    result.bugs += bug + "\n"

                for manualcase_id in [manualcase.id for manualcase in failure.manualcases]:
                    if manualcase_id not in result.manualcases:
                        result.manualcases += manualcase_id + "\n"

        if NoMatchingFailure:
            result.error = 'UNKNOWN FAILURE'
            print "UNKNOWN FAILURE For" + str(this_autocase)
        else:
            print "Manual Case Failure" + str(result.manualcases)

    elif result.skip:
        print "SKIPPED" + str(this_autocase)
        pass

    else:
        # Test case passed
        ManualCasePassed = []
        ManualCaseUncovered = []
        ManualCaseFailed = []
        for manualcase in this_autocase.manualcases:
            for related_autocase in manualcase.autocases:
                # Check all related autocases covering the same manual case,
                # manualcase can be marked as passed until all auto cases are passed.
                if related_autocase == this_autocase:
                    continue
                related_result = Result.query.get((result.run_id, related_autocase.id))
                if not related_result:
                    ManualCaseUncovered.append(manualcase)
                    break

                if related_result.failure is not None:
                    ManualCaseFailed.append(manualcase)
                    break

            if manualcase not in ManualCaseUncovered and manualcase not in ManualCaseFailed:
                ManualCasePassed.append(manualcase)

        # Generate errors and manualcases attr and
        # updated related auto cases
        for manualcase in ManualCaseUncovered:
            error = "UNCOVER " + manualcase.id
            result.error += error + "\n"

            # Related autocases results, remove passed manualcase, add UNCOVER error
            for related_autocase in manualcase.autocases:
                related_result = Result.query.get((result.run_id, related_autocase.id))
                if not related_result or related_result.failure is not None:
                    continue

                if related_autocase == this_autocase:
                    continue

                manualcases = related_result.manualcases.split("\n")
                manualcases = filter(lambda x: x != manualcase.id, manualcases)
                related_result.manualcases = "\n".join(manualcases)

                if error not in related_result.error:
                    related_result.error += error + "\n"

                session.add(related_result)

        for manualcase in ManualCasePassed:
            result.manualcases += manualcase.id + "\n"
            print "Passed manual case " + str(manualcase)

            # Related autocases results, remove UNCOVER error, and add passed manualcase
            for related_autocase in manualcase.autocases:
                related_result = Result.query.get((result.run_id, related_autocase.id))
                if not related_result or related_result.failure is not None:
                    continue

                if related_autocase == this_autocase:
                    continue

                errors = result.error.split("\n")
                errors = filter(lambda x: x != "UNCOVER " + manualcase.id, errors)
                related_result.error = "\n".join(errors)

                if not manualcase.id in related_result.manualcases:
                    related_result.manualcases += manualcase.id + "\n"

                session.add(related_result)

class CaseResultList(Resource):
    """
    Auto case results of a Auto run record
    """
    def get(self, run_id):
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        results = run.results.all()
        ret = []
        for run in results:
            ret.append(run.as_dict())
        return ret

    def post(self, run_id):
        args = CaseResultParser.parse_args()
        result = args
        result['run_id'] = run_id
        result['run'] = Run.query.get(run_id)

        if Result.query.get((run_id, args['case'])):
            return {'message': 'Case already exist'}, 400

        if result['failure'] and result['skip']:
            return {'message': 'failure and skip can\'t be set at the same time'}, 400

        result_instance = Result(**result)

        if not any(key in request.json.keys() for key in ['error', 'manualcases', 'bugs']):
            check_test_result(result_instance, db.session)

        try:
            db.session.add(result_instance)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        return result_instance.as_dict()


class CaseResultDetail(Resource):
    def get(self, run_id, case_name):
        res = Result.query.get((run_id, case_name))
        if not res:
            return {'message': 'Result doesn\'t exists'}, 400
        return res.as_dict()

    def put(self, run_id, case_name):
        res = Result.query.get((run_id, case_name))
        if not res:
            return {'message': 'Result doesn\'t exists'}, 400

        args = CaseResultUpdateParser.parse_args()
        result = args
        result['run_id'] = run_id
        result['run'] = Run.query.get(run_id)

        for key in request.json.keys():
            setattr(res, (key), result[(key)])

        if not any(key in request.json.keys() for key in ['error', 'manualcases', 'bugs']):
            check_test_result(res, db.session)

        db.session.add(res)
        db.session.commit()

        return res.as_dict()



class ErrorList(Resource):
    def get(self):
        ResultWithError = Result.query.filter(Result.error.isnot(None))
        ret = []
        for error in ResultWithError:
            ret.append(error.as_dict())
        return ret


api.add_resource(TestRunList, '/api/run/', endpoint='test_run_list')
api.add_resource(TestRunDetail, '/api/run/<int:run_id>/', endpoint='test_run_detail')
api.add_resource(CaseResultList, '/api/run/<int:run_id>/results/', endpoint='case_result_list')
api.add_resource(CaseResultDetail, '/api/run/<int:run_id>/results/<string:case_name>', endpoint='case_result_detail')
api.add_resource(ErrorList, '/api/error/', endpoint='error_list')

@app.route('/table/run/', methods=['GET'])
def test_run_table():
    return column_to_table(
        Run,
        TestRunList().get(),
        200)

@app.route('/table/run/<int:run_id>/results', methods=['GET'])
def case_result_table(run_id):
    return column_to_table(
        Result,
        CaseResultList().get(run_id),
        200,
        extra_column=['status']
    )

@app.route('/submit', methods=['GET'])
#TODO submit passed first, then failed
def submit_to_polarion():
    submitted_runs = []
    error_runs = []
    class ConflictError(Exception):
        pass

    for test_run in Run.query.filter(Run.submitted == False):
        polaroin_testrun = Polarion.TestRunRecord(
            project=test_run.project,
            name=test_run.name,
            description="CI Job: " + str(test_run.description),
            type=test_run.type,
            date=test_run.date,
            build=test_run.build,
            version=test_run.version,
            arch=test_run.arch
        )

        manual_cases = {}

        try:
            for record in Result.query.filter(Result.run_id == test_run.id):
                if record.bugs:
                    result = 'failed'
                elif record.error or record.status == "Illegal":
                    raise ConflictError()
                else:
                    result = 'passed'

                manualcase_ids = record.manualcases.split("\n")
                for id in manualcase_ids:
                    if id == "":
                        continue
                    if id in manual_cases:
                        if manual_cases[id]['result'] != result:
                            raise RuntimeError("Result Inconsistent: %s" % id)
                        manual_cases[id]['duration'] += record.time
                    else:
                        manual_cases[id] = {
                            "result": result,
                            "duration": record.time,  # Float
                        }
        except ConflictError:
            error_runs.append(test_run.as_dict())
            continue

        for case in manual_cases:
            polaroin_testrun.add_record(
                case=case,
                result=manual_cases[case]['result'],
                duration=manual_cases[case]['duration'],
                datetime=test_run.date,  # Datetime
                executed_by='CI',
                comment='Dashboard Generated Record'
            )

        with Polarion.TestRunSession() as session:
            polaroin_testrun.submit(session)

        test_run.submitted = True
        db.session.add(test_run)
        db.session.commit()
        submitted_runs.append(test_run.as_dict())

    return jsonify( {'submitted': submitted_runs, 'error': error_runs, })


if __name__ == '__main__':
    bootstrap()
    manager.run()
