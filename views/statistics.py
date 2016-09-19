from datetime import datetime
from flask import Blueprint, Markup, render_template, request, jsonify
from model import db, Run, AutoResult, ManualResult, refresh_result, Run
from sqlalchemy.orm import load_only, joinedload
from collections import Counter

dashboard_statistics = Blueprint('dashboard_statistics', __name__)
CHUNCK_SIZE = 300

@dashboard_statistics.route('/auto/', methods=['GET'])
@dashboard_statistics.route('/run/<string:test_run>/auto/', methods=['GET'])
def autocase_statistics(test_run=None):
    def parse_date(keyword):
        try:
            ret = datetime(*[int(num) for num in request.args.get(keyword).split('-')])
        except (AttributeError, TypeError, ValueError):
            ret = None
        return ret

    date_after = parse_date('date_after')
    date_before = parse_date('date_before')

    query = AutoResult.query

    if date_after or date_before or test_run:
        query = query.options(joinedload('run'))

    if date_before:
        query = query.filter(Run.date < date_before)

    if date_after:
        query = query.filter(Run.date > date_after)

    if test_run:
        query = query.filter(Run.name == test_run)

    cases = query.options(load_only('output', 'failure', 'skip', 'case')).yield_per(CHUNCK_SIZE)

    ret = {}

    for result_instance in cases:
        statistics = ret.setdefault(result_instance.case, {
            'failed': 0,
            'passed': 0,
            'skipped': 0,
            'invalid': 0,
            'total': 0,
        })
        statistics['total'] += 1
        if result_instance.result is None:
            statistics['invalid'] += 1
        else:
            statistics[result_instance.result] += 1
    return jsonify(ret), 200


@dashboard_statistics.route('/auto/<string:case>', methods=['GET'])
def autocase_detail(case):
    cases = AutoResult.query.filter(AutoResult.case == case)\
            .options(joinedload('run'))\
            .yield_per(CHUNCK_SIZE)

    ret = {}

    for result_instance in cases:
        statistics = ret.setdefault(result_instance.case, {
            'failed': [],
            'passed': [],
            'skipped': [],
            'invalid': [],
            'total': 0,
        })
        statistics['total'] += 1
        if result_instance.result is None:
            statistics['invalid'].append(result_instance.run.as_dict())
        else:
            statistics[result_instance.result].append(result_instance.run.as_dict())
    return jsonify(ret), 200


@dashboard_statistics.route('/run/', methods=['GET'])
@dashboard_statistics.route('/run/<string:name>', methods=['GET'])
def testrun_statistics(name=None):
    if name:
        runs = Run.query.filter(Run.name == name)\
                .options(load_only('date', 'name')).yield_per(CHUNCK_SIZE)
    else:
        runs = Run.query\
                .options(load_only('date', 'name')).yield_per(CHUNCK_SIZE)
    ret = {}

    for run in runs:
        statistics = {'date': run.date.isoformat()}
        statistics.update(run.get_statistics())
        if run.name in ret.keys():
            ret[run.name].append(statistics)
        else:
            ret[run.name] = [statistics]
    return jsonify(ret), 200
