import datetime
import re

from model import db, AutoResult, ManualResult, Run, Tag, Property
from flask import Blueprint, request
from flask_restful import Resource, Api, reqparse, inputs
from sqlalchemy.exc import IntegrityError

restful_api = Blueprint('restful_api', __name__)

api = Api(restful_api)

TestRunParser = reqparse.RequestParser(bundle_errors=True)
TestRunParser.add_argument('name', required=True)
TestRunParser.add_argument('component', required=True)
TestRunParser.add_argument('build', required=None)
TestRunParser.add_argument('product', required=None)
TestRunParser.add_argument('version', required=None)
TestRunParser.add_argument('arch', required=True)
TestRunParser.add_argument('type', required=True)
TestRunParser.add_argument('framework', required=True)
TestRunParser.add_argument('project', required=True)
TestRunParser.add_argument('date', type=inputs.datetime_from_iso8601, required=True)
TestRunParser.add_argument('ci_url', required=True)
TestRunParser.add_argument('description', default=None)
TestRunParser.add_argument('tags', type=str, action='append', default=[])
TestRunParser.add_argument('properties', type=dict, default={})


AutoResultParser = reqparse.RequestParser(bundle_errors=True)
AutoResultParser.add_argument('case', required=True)
AutoResultParser.add_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=True)
AutoResultParser.add_argument('output', required=True)
AutoResultParser.add_argument('failure', default=None)
AutoResultParser.add_argument('source', default=None)
AutoResultParser.add_argument('skip', default=None)
AutoResultParser.add_argument('error', default=None)
AutoResultParser.add_argument('linkage_result', default=None)
AutoResultParser.add_argument('comment', default=None)


AutoResultUpdateParser = AutoResultParser.copy()
AutoResultUpdateParser.replace_argument('output', required=False)
AutoResultUpdateParser.replace_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=False)
AutoResultUpdateParser.replace_argument('case', required=False)


ManualResultUpdateParser = reqparse.RequestParser(bundle_errors=True)
ManualResultUpdateParser.add_argument('result', required=False)


class TestRunList(Resource):
    def get(self):
        runs = Run.query.all()
        ret = []
        for run in runs:
            ret.append(run.as_dict(detailed=True))
        return ret

    def post(self):
        args = TestRunParser.parse_args()
        try:
            run = Run(**args)
            db.session.add(run)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if "_test_run_id_uc" in  e.message:
                run = Run.query.filter(Run.name == args['name'],
                                       Run.date == args['date']
                                      ).one()
                return run.as_dict(), 400
            else:
                raise e
        return run.as_dict()


class TestRunDetail(Resource):
    def get(self, run_id):
        run = Run.query.get(run_id)
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        return run.as_dict(detailed=True)

    def delete(self, run_id):
        res = Run.query.get(run_id)
        if not res:
            return {'message': 'Test Run doesn\'t exists'}, 400
        for record in AutoResult.query.filter(AutoResult.run_id == run_id):
            db.session.delete(record)
        for record in ManualResult.query.filter(ManualResult.run_id == run_id):
            db.session.delete(record)
        for record in Property.query.filter(Property.run_id == run_id):
            db.session.delete(record)
        res.tags = []
        db.session.commit()
        db.session.delete(res)
        db.session.commit()
        return res.as_dict()

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
            if res.result != "missing":
                return res.as_dict(), 400
            else:
                db.session.delete(res)

        result_instance = AutoResult(**result)

        try:
            db.session.add(result_instance)
            result_instance.gen_linkage_result(session=db.session)
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


api.add_resource(TestRunList, '/run/', endpoint='test_run_list')
api.add_resource(TestRunDetail, '/run/<int:run_id>/', endpoint='test_run_detail')
api.add_resource(AutoResultList, '/run/<int:run_id>/auto/', endpoint='auto_result_list')
api.add_resource(AutoResultDetail, '/run/<int:run_id>/auto/<string:case_name>/', endpoint='auto_result_detail')
api.add_resource(ManualResultList, '/run/<int:run_id>/manual/', endpoint='manual_result_list')
api.add_resource(ManualResultDetail, '/run/<int:run_id>/manual/<string:case_name>/', endpoint='manual_result_detail')
api.add_resource(ErrorList, '/error/', endpoint='error_list')
