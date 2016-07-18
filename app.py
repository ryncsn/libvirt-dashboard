#!/usr/bin/env python

from flask import Flask, request
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_restful import Resource, Api, reqparse, inputs
from flask_sqlalchemy import SQLAlchemy

from requests import HTTPError

import utils.caselink as CaseLink
#import utils.polarion as Polarion

app = Flask(__name__)
app.config.from_object('config.ActiveConfig')

db = SQLAlchemy(app)
from model import *

api = Api(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


def bootstrap():
    db.create_all()


TestRunParser = reqparse.RequestParser(bundle_errors=True);
TestRunParser.add_argument('arch', required=True);
TestRunParser.add_argument('type', required=True);
TestRunParser.add_argument('name', required=True);
TestRunParser.add_argument('date', type=inputs.datetime_from_iso8601, required=True);
TestRunParser.add_argument('build', required=None);
TestRunParser.add_argument('project', required=True);
TestRunParser.add_argument('component', required=True);
TestRunParser.add_argument('framework', required=None);
TestRunParser.add_argument('description', default=None);


CaseResultParser = reqparse.RequestParser(bundle_errors=True);
CaseResultParser.add_argument('case', required=True);
CaseResultParser.add_argument('time', type=inputs.regex('^[0-9]+.[0-9]+$'), required=True);
CaseResultParser.add_argument('output', required=True);
CaseResultParser.add_argument('failure', default=None);
CaseResultParser.add_argument('skip', default=None);
CaseResultParser.add_argument('source', default='');


class TestRunList(Resource):
    def get(self):
        runs = Run.query.all()
        ret = [];
        for run in runs:
            ret.append(run.as_dict())
        return ret


    def post(self):
        args = TestRunParser.parse_args()
        run = args;
        run = Run(args);
        db.session.add(run);
        try:
            db.session.commit();
        except Exception as e:
            db.session.rollback();
            raise e
        return run.as_dict();


class TestRunDetail(Resource):
    def get(self, run_id):
        run = Run.query.get(run_id);
        if not run:
            return {'message': 'Test Run doesn\'t exists'}, 400
        results = run.results.all()
        ret = [];
        for run in results:
            ret.append(run.as_dict())
        return ret


    def post(self, run_id):
        args = CaseResultParser.parse_args()
        result = args;
        result['run_id'] = run_id;
        result['run'] = Run.query.get(run_id);

        if Result.query.get((run_id, args['case'])):
            return {'message': 'Case already exist'}, 400

        if result['failure'] and result['skip']:
            return {'message': 'failure and skip can\'t be set at the same time'}, 400


        try:
            # TODO better error handling
            autocase = CaseLink.AutoCase(result['case']);
            manualcases = autocase.manualcases
            bugs = autocase.bugs
        except HTTPError as e:
            if e.response.status_code == 404:
                return {'message': 'Auto case not included in caselink'}, 400
            else:
                return {'message': 'Caselink didn\'t response in a expected way'}, 400

        # TODO use another table or drop these attributes.
        result['bugs'] = "\n".join(bugs)
        result['manualcases'] = "\n".join(manualcases)
        result_instance = Result(result)
        db.session.add(result_instance);

        if result['failure']:
            conflict = True
            for bug in bugs:
                if result['failure'] == bug['message']:
                    conflict = False
                    # TODO Bug check and Polarion update
                    pass
            if conflict:
                conflict = Conflict({'resolve': 'NEW'})
                conflict.results.append(result_instance)
                db.session.add(conflict)

        elif result['skip']:
            result['skip'] = result['skip'].get('message')

        else:
            # TODO
            # Check if all related auto cases passed, then perform Polarion update
            pass

        try:
            db.session.commit();
        except Exception as e:
            db.session.rollback();
            raise e
        return result_instance.as_dict()


class CaseResultDetail(Resource):
    def get(self, run_id, case_name):
        res = Result.query.get((run_id, case_name))
        if not res:
            return {'message': 'Result doesn\'t exists'}, 400
        return res.as_dict()


class ConflictList(Resource):
    def get(self):
        conflicts = Conflict.query.all()
        ret = [];
        for conflict in conflicts:
            ret.append(conflict.as_dict())
        return ret


class ConflictDetail(Resource):
    def get(self, run_id, case_name):
        res = Result.query.get((run_id, case_name))
        if not res or not res.conflict:
            return {'message': 'Conflict doesn\'t exists'}, 400
        return res.conflict.as_dict()


api.add_resource(TestRunList, '/run/')
api.add_resource(TestRunDetail, '/run/<int:run_id>/')
api.add_resource(CaseResultDetail, '/run/<int:run_id>/<string:case_name>')
api.add_resource(ConflictDetail, '/run/<int:run_id>/<string:case_name>/conflict/')
api.add_resource(ConflictList, '/conlicts/')


if __name__ == '__main__':
    bootstrap()
    manager.run()
