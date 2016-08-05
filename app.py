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
    resp = make_response(render_template('column_table.html',
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
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        return run.as_dict()

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


def _update_manual(autocase, manualcase_id, session,
                   expected_results=None, from_results=None, to_result=None, comment=''):
    manualcase = get_or_create(session, ManualResult, run_id=autocase.run_id, case=manualcase_id)
    if expected_results:
        if not manualcase.result in expected_results:
            #print "expected + " + str(expected_results)+ "get "+ str(manualcase.result)
            return None
    if to_result:
        if not from_results or manualcase.result in from_results:
            manualcase.result = to_result
        else:
            #print "expected + " + str(from_results)+ "get "+str(manualcase.result)
            pass
    manualcase.time += float(autocase.time)
    if not manualcase.comment:
        manualcase.comment = comment
    else:
        manualcase.comment += "\n" + comment
    return manualcase


def gen_manual_case(result, caselink, session):
    """
    Take a unsaved result instance, generate it's ralated manual cases.

    Need to clean all manual cases for a test run first.
    """

    if not caselink:
        return (False, "No caselink")

    if result.result.startswith('skipped'):
        if not caselink.manualcases or len(caselink.manualcases) == 0:
            return (False, "No manual case for skipped auto case")
        for caselink_manualcase in caselink.manualcases:
            if not _update_manual(result, caselink_manualcase.id, session,
                                  expected_results = [None, 'incomplete', 'failed'],
                                  from_results = [None], to_result = 'incomplete',
                                  comment = ('Skipped Auto case: "%s"\n' % result.case)):
                #print "Skip for non incomplete case"
                pass
        return (True, "Manual case updated.")

    elif result.result == 'failed':
        # Auto Case failed with message <result['failure']>
        if not caselink.failures or len(caselink.failures) == 0:
            return (False, "No manual case for failed auto case")
        for failure in caselink.failures:
            if re.match(failure.failure_regex, result.failure) is not None:
                for case in failure.manualcases:
                    if not _update_manual(result, case.id, session,
                                          expected_results = [None, 'incomplete', 'failed'],
                                          from_results = [None, 'incomplete'], to_result = 'failed',
                                          comment = ('Failed auto case: "%s", BUG: "%s"\n' %
                                                     (failure.bug.id, result.case))):
                        #print "Failed for non incomplete case"
                        pass
        return (True, "Manual Case marked failed.")

    elif result.result == 'passed':
        if not caselink.manualcases or len(caselink.manualcases) == 0:
            return (False, "No manual case for passed auto case")
        for caselink_manualcase in caselink.manualcases:
            ManualCasePassed=True
            for related_autocase in caselink_manualcase.autocases:
                related_result = AutoResult.query.get((result.run_id, related_autocase.id))
                if not related_result and related_autocase != caselink:
                    # This auto case passed, but some related auto case are not submitted yet.
                    ManualCasePassed = False
                    if not _update_manual(result, caselink_manualcase.id, session,
                                          expected_results = [None, 'incomplete', 'failed'],
                                          from_results = [None], to_result = 'incomplete',
                                          comment = ('Passed Auto case: "%s"\n' % result.case)):
                        #print "Incomplete case makred passed"
                        pass
                    break

                elif related_result.skip is not None:
                    # This auto case passed, but some related auto case are skipped.
                    ManualCasePassed = False
                    if not _update_manual(result, caselink_manualcase.id, session,
                                          expected_results = [None, 'incomplete', 'failed'],
                                          from_results = [None], to_result = 'incomplete',
                                          comment = ('Passed Auto case: "%s"\n' % result.case)):
                        #print "Skipped case makred passed"
                        pass
                    break

                elif related_result.failure is not None:
                    # This auto case passed, but some related auto case are failed.
                    ManualCasePassed = False
                    if not _update_manual(result, caselink_manualcase.id, session,
                                          expected_results = [None, 'failed'],
                                          from_results = [None], to_result = 'incomplete',
                                          comment = ('Passed Auto case: "%s"\n' % result.case)):
                        #print "Manual already failed, not properly marked"
                        pass
                    break

            if ManualCasePassed:
                # This auto case passed, and all related auto case are passed.
                if not _update_manual(result, caselink_manualcase.id, session,
                                      expected_results = [None, 'incomplete'],
                                      from_results = [None, 'incomplete'], to_result = 'passed',
                                      comment = ('Passed Auto case: "%s"\n' % result.case)):
                    #print "Trying to pass already failed case"
                    pass
        return (True, "Manual Case updated.")


def refresh_result(result, session, gen_manual=True, gen_error=True, gen_result=True):
    """
    Take a unsaved result instance, rewrite it's error and result
    with data in caselink.
    """
    # Failed -> look up in failures, if any bug matches, mark manualcase failed
    # Passed -> look up in linkages(manualcases), if all related autocase of a manualcase
    #           passed, mark the manualcase passed
    # Mark error when lookup failed
    if gen_error:
        result.error = None
    if gen_result:
        result.result = None

    def _set_error(err):
        if gen_error:
            result.error = err

    def _set_result(res):
        if gen_result:
            result.result = res

    try:
        this_autocase = CaseLink.AutoCase(result.case).refresh()
    except HTTPError as e:
        if e.response.status_code == 404:
            _set_error('No Caselink')
        else:
            _set_error('Caselink Failure')
        return False, result.error

    if result.skip:
        _set_result('skipped')

    elif result.failure:
        # Auto Case failed with message <result['failure']>
        BugFound = False
        for failure in this_autocase.failures:
            if re.match(failure.failure_regex, result.failure) is not None:
                BugFound = True
                _set_result('failed')

        if not BugFound:
            _set_error('Unknown Issue')

    elif result.output:
        if not this_autocase.manualcases or len(this_autocase.manualcases) == 0:
            _set_error('No Linkage')
        else:
            _set_result('passed')

    if not result.result:
        return False, result.error

    else:
        if gen_manual:
            return gen_manual_case(result, this_autocase, session)
        else:
            return True, result.result


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

        (success, message) = refresh_result(result_instance, db.session)

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

        gen_result =  not 'result' in request.json.keys()
        gen_error =  not 'error' in request.json.keys()
        (success, message) = refresh_result(res, db.session, gen_result = gen_result, gen_error = gen_error)

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
    columns = ["case", "time", "error", "result"]
    resp = make_response(render_template('resolve_auto.html',
                                         column_names=columns,
                                         column_datas=columns,
                                         ajax='/api/run/' + str(run_id) + '/auto/'),
                         200)
    return resp

@app.route('/table/run/<int:run_id>/manual/resolve', methods=['GET'])
def resolve_manualcase(run_id):
    columns = ["case", "time", "comment", "result"]
    resp = make_response(render_template('resolve_manual.html',
                                         column_names=columns,
                                         column_datas=columns,
                                         ajax='/api/run/' + str(run_id) + '/manual/'),
                         200)
    return resp


@app.route('/trigger/run/<int:run_id>/refresh', methods=['GET'])
def refresh_testrun(run_id):
    ret = {}
    ManualResult.query.filter(ManualResult.run_id == run_id).\
            delete(synchronize_session=False)

    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        (success, message) = refresh_result(result_instance, db.session)
        db.session.add(result_instance)
        if not success:
            ret[result_instance.case] = message

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    if len(ret.keys()) == 0:
        return jsonify({'message': 'success'}), 200
    return jsonify(ret), 200


@app.route('/trigger/run/<int:run_id>/auto/refresh', methods=['GET'])
def refresh_auto(run_id):
    ret = {}
    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        (success, message) = refresh_result(result_instance, db.session, gen_manual=False)
        db.session.add(result_instance)
        if not success:
            ret[result_instance.case] = message

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    if len(ret.keys()) == 0:
        return jsonify({'message': 'success'}), 200
    return jsonify(ret), 200


@app.route('/trigger/run/<int:run_id>/manual/refresh', methods=['GET'])
def refresh_manual(run_id):
    ret = {}
    ManualResult.query.filter(ManualResult.run_id == run_id).\
            delete(synchronize_session=False)

    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        (success, message) = refresh_result(result_instance, db.session, gen_error=False, gen_result=False)
        db.session.add(result_instance)
        if not success:
            ret[result_instance.case] = message

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    if len(ret.keys()) == 0:
        return jsonify({'message': 'success'}), 200
    return jsonify(ret), 200


@app.route('/trigger/run/submit', methods=['GET'])
@app.route('/trigger/run/<int:run_id>/submit', methods=['GET'])
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
