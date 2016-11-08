from datetime import datetime
from flask import Blueprint, Markup, render_template, request, jsonify
from model import db, Run, AutoResult, ManualResult, Run
from sqlalchemy.orm import load_only, joinedload
from collections import Counter

dashboard_statistics = Blueprint('dashboard_statistics', __name__)
CHUNCK_SIZE = 300


def parse_date(keyword):
    try:
        ret = datetime(*[int(num) for num in request.args.get(keyword).split('-')])
    except (AttributeError, TypeError, ValueError):
        ret = None
    return ret


@dashboard_statistics.route('/auto/', methods=['GET'])
@dashboard_statistics.route('/run/<string:test_run>/auto/', methods=['GET'])
def autocase_statistics(test_run=None):
    def parse_date(keyword):
        try:
            ret = datetime(*[int(num) for num in request.args.get(keyword).split('-')])
        except (AttributeError, TypeError, ValueError):
            ret = None
        return ret

    after = parse_date('after')
    before = parse_date('before')

    query = AutoResult.query

    if after or before or test_run:
        query = query.join(Run)

    if before:
        query = query.filter(Run.date < before)

    if after:
        query = query.filter(Run.date > after)

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
    after = parse_date('after')
    before = parse_date('before')

    try:
        limit = int(request.args.get('limit', None))
    except Exception:
        limit = None

    query = Run.query

    if name:
        query = query.filter(Run.name == name)

    if before:
        query = query.filter(Run.date < before)

    if after:
        query = query.filter(Run.date > after)

    runs = query.options(load_only('date', 'name')).yield_per(CHUNCK_SIZE)
    ret = {}

    for run in runs:
        ret.setdefault(run.name, [])
        if limit is not None and len(ret[run.name]) >= limit:
            continue
        statistics = {'date': run.date.isoformat()}
        statistics.update(run.get_statistics())
        ret[run.name].append(statistics)

    return jsonify(ret), 200


@dashboard_statistics.route('/run/last/', methods=['GET'])
@dashboard_statistics.route('/run/last/<int:limit>', methods=['GET'])
def testrun_lastest(limit=None):
    query = Run.query.order_by(Run.date.desc())

    if limit:
        query = query.limit(limit)

    runs = query.options(load_only('date', 'name', 'id')).yield_per(CHUNCK_SIZE)
    ret = []

    for run in runs:
        ret.append(run.as_dict(detailed=True))

    return jsonify(ret), 200
