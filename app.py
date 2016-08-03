#!/usr/bin/env python

from flask import Flask, request, Markup
from flask import render_template, make_response, jsonify
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_restful import Resource, Api, reqparse, inputs
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from requests import HTTPError

import datetime

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


AutoResultParser = reqparse.RequestParser(bundle_errors=True)
AutoResultParser.add_argument('case', required=True)
AutoResultParser.add_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=True)
AutoResultParser.add_argument('output', required=True)
AutoResultParser.add_argument('failure', default=None)
AutoResultParser.add_argument('source', default=None)
AutoResultParser.add_argument('skip', default=None)
AutoResultParser.add_argument('error', default=None)
AutoResultParser.add_argument('result', default=None)
AutoResultParser.add_argument('comment', default=None)

AutoResultUpdateParser = AutoResultParser.copy()
AutoResultUpdateParser.replace_argument('output', required=False)
AutoResultUpdateParser.replace_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=False)
AutoResultUpdateParser.replace_argument('case', required=False)

ManualResultUpdateParser = reqparse.RequestParser(bundle_errors=True)
ManualResultUpdateParser.add_argument('result', required=False)

def column_to_table(model, ajax_url, code, extra_column=[]):
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
                                         ajax=ajax_url), 200)
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
        run = Run(**args)
        db.session.add(run)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if "UNIQUE constraint failed" in  e.message:
                run = Run.query.filter(Run.name == args['name'],
                                       Run.type == args['type'],
                                       Run.build == args['build'],
                                       Run.version == args['version'],
                                       Run.arch == args['arch'],
                                       Run.date == args['date']).one()
                return run.as_dict(), 400
            else:
                raise e
        return run.as_dict()


class TestRunDetail(Resource):
    def get(self, run_id):
        args = TestRunParser.parse_args()
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        return ret.as_dict()

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


def gen_manual_case_and_error(result, session):
    """
    Take a unsaved result instance,
    Check with other results in database and caselink.

    'result' should only have attribute 'case', 'output',
    and one of 'failure', 'skip', other attributes will be genereted.
    """
    # Failed -> look up in failures, if any bug matches, mark manualcase failed
    # Passed -> look up in linkages(manualcases), if all related autocase of a manualcase
    #           passed, mark the manualcase passed
    # Mark error when lookup failed

    this_autocase = CaseLink.AutoCase(result.case)

    if result.skip:
        #TODO
        result.result = 'Skip'
        pass

    elif result.failure:
        # Auto Case failed with message <result['failure']>
        BugMatched = False
        for failure in this_autocase.failures:
            if re.match(failure.failure_regex, result.failure) is not None:
                BugMatched = True

                for case in failure.manualcases:
                    manualcase = get_or_create(session, ManualResult, run_id=result.run_id, case=case.id)
                    manualcase.result = 'failed'
                    manualcase.time += float(result.time)
                    if not manualcase.comment:
                        manualcase.comment = ''
                    if failure.bug.id not in manualcase.comment:
                        manualcase.comment += ('\nFailed By BUG: "%s", Auto case: "%s"' %
                                                (failure.bug.id, result.case))

        if not BugMatched:
            result.error = 'Unknown Issue'
        else:
            result.result = 'Known Issue'
        return

    elif result.output:
        ManualCasePassed = []
        ManualCaseImcomplete = []
        ManualCaseAlreadyFailed = []

        if not this_autocase.manualcases or len(this_autocase.manualcases) == 0:
            result.error = 'No Linkage'
            return

        for caselink_manualcase in this_autocase.manualcases:
            for related_autocase in caselink_manualcase.autocases:
                # Check all related autocases covering the same manual case,
                # manualcase can be marked as passed only if all ralated auto cases are passed.
                related_result = AutoResult.query.get((result.run_id, related_autocase.id))

                if not related_result or related_result.skip is not None:
                    if related_autocase != this_autocase:
                        manualcase = get_or_create(session, ManualResult, run_id=result.run_id, case=caselink_manualcase.id)
                        manualcase.result = 'incomplete'
                        manualcase.time += float(result.time)
                        if not manualcase.comment:
                            manualcase.comment = ''
                        if result.case not in manualcase.comment:
                            manualcase.comment += ('\nPassed Auto case: "%s"' % result.case)

                elif related_result.failure is not None:
                    # Failed Already
                    pass

                else:
                    manualcase = get_or_create(session, ManualResult, run_id=result.run_id, case=caselink_manualcase.id)
                    manualcase.result = 'passed'
                    manualcase.time += float(result.time)
                    if not manualcase.comment:
                        manualcase.comment = ''
                    if result.case not in manualcase.comment:
                        manualcase.comment += ('\nPassed Auto case: "%s"' % result.case)
        result.result = 'Pass'


class AutoResultList(Resource):
    """
    Auto case results of a Auto run record
    """
    def get(self, run_id):
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        results = run.auto_results.all()
        ret = []
        for run in results:
            ret.append(run.as_dict())
        return ret

    def post(self, run_id):
        args = AutoResultParser.parse_args()
        result = args
        result['run_id'] = run_id
        result['run'] = Run.query.get(run_id)

        res = AutoResult.query.get((run_id, args['case']))
        if res:
            return res.as_dict(), 400

        result_instance = AutoResult(**result)

        try:
            gen_manual_case_and_error(result_instance, db.session)
        except HTTPError as e:
            if e.response.status_code == 404:
                result_instance.error = 'No Caselink'
            else:
                result_instance.error = 'Caselink Failure'

        try:
            db.session.add(result_instance)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        return result_instance.as_dict()


class AutoResultDetail(Resource):
    def get(self, run_id, case_name):
        res = AutoResult.query.get((run_id, case_name))
        if not res:
            return {'message': 'AutoResult doesn\'t exists'}, 400
        return res.as_dict(detailed=True)

    def delete(self, run_id, case_name):
        res = AutoResult.query.get((run_id, case_name))
        if not res:
            return {'message': 'AutoResult doesn\'t exists'}, 400
        db.session.delete(res)
        db.session.commit()
        return res.as_dict()

    def put(self, run_id, case_name):
        res = AutoResult.query.get((run_id, case_name))
        if not res:
            return {'message': 'AutoResult doesn\'t exists'}, 400

        args = AutoResultUpdateParser.parse_args()
        result = args
        result['run_id'] = run_id
        result['run'] = Run.query.get(run_id)

        for key in request.json.keys():
            setattr(res, (key), result[(key)])

        if not 'result' in request.json.keys():
            try:
                gen_manual_case_and_error(res, db.session)
            except HTTPError as e:
                if e.response.status_code == 404:
                    result_instance.error = 'No Caselink'
                else:
                    result_instance.error = 'Caselink Failure'

        db.session.add(res)
        db.session.commit()

        return res.as_dict()


class ManualResultList(Resource):
    """
    Auto case results of a Auto run record
    """
    def get(self, run_id):
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        results = run.manual_results.all()
        ret = []
        for run in results:
            ret.append(run.as_dict())
        return ret


class ManualResultDetail(Resource):
    def get(self, run_id, case_name):
        res = ManualResult.query.get((run_id, case_name))
        if not res:
            return {'message': 'ManualResult doesn\'t exists'}, 400
        return res.as_dict()

    def delete(self, run_id, case_name):
        res = ManualResult.query.get((run_id, case_name))
        if not res:
            return {'message': 'ManualResult doesn\'t exists'}, 400
        db.session.delete(res)
        db.session.commit()
        return res.as_dict()

    def put(self, run_id, case_name):
        res = ManualResult.query.get((run_id, case_name))
        if not res:
            return {'message': 'ManualResult doesn\'t exists'}, 400

        args = ManualResultUpdateParser.parse_args()
        result = args
        result['run_id'] = run_id
        result['run'] = Run.query.get(run_id)

        for key in args.keys():
            setattr(res, (key), result[(key)])

        db.session.add(res)
        db.session.commit()

        return res.as_dict()


class ErrorList(Resource):
    def get(self):
        ResultWithError = AutoResult.query.filter(AutoResult.error.isnot(None))
        ret = []
        for error in ResultWithError:
            ret.append(error.as_dict())
        return ret


api.add_resource(TestRunList, '/api/run/', endpoint='test_run_list')
api.add_resource(TestRunDetail, '/api/run/<int:run_id>/', endpoint='test_run_detail')
api.add_resource(AutoResultList, '/api/run/<int:run_id>/auto/', endpoint='auto_result_list')
api.add_resource(AutoResultDetail, '/api/run/<int:run_id>/auto/<string:case_name>/', endpoint='auto_result_detail')
api.add_resource(ManualResultList, '/api/run/<int:run_id>/manual/', endpoint='manual_result_list')
api.add_resource(ManualResultDetail, '/api/run/<int:run_id>/manual/<string:case_name>/', endpoint='manual_result_detail')
api.add_resource(ErrorList, '/api/error/', endpoint='error_list')

@app.route('/table/run/', methods=['GET'])
def test_run_table():
    return column_to_table(
        Run,
        '/api/run/',
        200)

@app.route('/table/run/<int:run_id>/auto/', methods=['GET'])
def auto_result_table(run_id):
    return column_to_table(
        AutoResult,
        '/api/run/' + str(run_id) + '/auto/',
        200)

@app.route('/table/run/<int:run_id>/manual/', methods=['GET'])
def manual_result_table(run_id):
    return column_to_table(
        ManualResult,
        '/api/run/' + str(run_id) + '/manual/',
        200)

@app.route('/table/run/<int:run_id>/auto/resolve', methods=['GET'])
def resolve_autocase(run_id):
    columns = AutoResult.__table__.columns
    columns = [str(col).split('.')[-1] for col in columns]
    resp = make_response(render_template('resolve_auto.html',
                                         column_names=columns,
                                         column_datas=columns,
                                         ajax='/api/run/' + str(run_id) + '/auto/'),
                         200)
    return resp

@app.route('/table/run/<int:run_id>/manual/resolve', methods=['GET'])
def resolve_manualcase(run_id):
    columns = ManualResult.__table__.columns
    columns = [str(col).split('.')[-1] for col in columns]
    resp = make_response(render_template('resolve_manual.html',
                                         column_names=columns,
                                         column_datas=columns,
                                         ajax='/api/run/' + str(run_id) + '/manual/'),
                         200)
    return resp


@app.route('/submit', methods=['GET'])
@app.route('/submit/<int:run_id>', methods=['GET'])
def submit_to_polarion(run_id=None):
    submitted_runs = []
    error_runs = []
    class ConflictError(Exception):
        pass

    if run_id:
        test_runs = Run.query.filter(Run.submit_date == None, Run.id == run_id)
    else:
        test_runs = Run.query.filter(Run.submit_date == None)

    for test_run in test_runs:
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

        try:
            for record in AutoResult.query.filter(AutoResult.run_id == test_run.id):
                print record
                if not record.result:
                    raise ConflictError()
        except ConflictError:
            error_runs.append(test_run.as_dict())
            continue

        for record in ManualResult.query.filter(ManualResult.run_id == test_run.id):
            polaroin_testrun.add_record(
                case=record.case,
                result=record.result,
                duration=record.time,
                datetime=test_run.date,  # Datetime
                executed_by='CI',
                comment=record.comment
            )

        with Polarion.PolarionSession() as session:
            polaroin_testrun.submit(session)

        #TODO issue a caselink backup

        test_run.submit_date = datetime.datetime.now()
        db.session.add(test_run)
        db.session.commit()
        submitted_runs.append(test_run.as_dict())

    return jsonify( {'submitted': submitted_runs, 'error': error_runs, })


if __name__ == '__main__':
    bootstrap()
    manager.run()
