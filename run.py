#!/usr/bin/env python

from flask import Flask, request
from flask_restful import Resource, Api, reqparse, inputs
import utils.caselink as CaseLink
import utils.polarion as Polarion


app = Flask(__name__)
api = Api(app)


def iso_date_string(param):
    return str(inputs.datetime_from_iso8601(param))


TestRunParser = reqparse.RequestParser(bundle_errors=True);
TestRunParser.add_argument('arch', required=True);
TestRunParser.add_argument('type', required=True);
TestRunParser.add_argument('name', required=True);
TestRunParser.add_argument('date', type=iso_date_string, required=True);
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
        return {'message': 'TBD'}

    def post(self):
        args = TestRunParser.parse_args()
        run = args;
        run['id'] = 1;
        return run;


class TestRun(Resource):
    def post(self, run_id):
        args = CaseResultParser.parse_args()
        autocase = CaseLink.AutoCase(args['case']);
        case = args;
        case['id'] = 1;
        case['run'] = run_id;
        case['manualcases'] = autocase.manualcases

        if case['failure'] and case['skip']:
            return {'message': 'failure and skip can\'t be set at the same time.'}, 400

        if case['failure']:
            case['bugs'] = bugs = autocase.bugs
            conflict = True
            for bug in bugs:
                if case['failure'] == bug['message']:
                    conflict = False
                    #Bug check and Polarion update
                    pass
            if conflict:
                #Setup new conflict entry
                pass
        elif case['skip']:
            case['skip'] = case['skip'].get('message')
        else:
            pass #Polarion update
        return case


class CaseResult(Resource):
    def get(self, run_id, case_name):
        return {'message': 'TBD'}


api.add_resource(TestRunList, '/run/')
api.add_resource(TestRun, '/run/<int:run_id>/')
api.add_resource(CaseResult, '/run/<int:run_id>/<string:case_name>')


if __name__ == '__main__':
    app.run(debug=True)
