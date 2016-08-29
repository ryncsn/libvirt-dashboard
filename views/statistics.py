from flask import Blueprint, Markup, render_template, request, jsonify
from model import db, AutoResult, ManualResult, refresh_result, Run
from collections import Counter

dashboard_statistics = Blueprint('dashboard_statistics', __name__)

@dashboard_statistics.route('/auto/<string:case>', methods=['GET'])
def autocase_statistics(case):
    statistics = {
        'failed': 0,
        'passed': 0,
        'skipped': 0,
        'invalid': 0,
        'total': 0,
    }
    ret = {case: statistics}

    for result_instance in AutoResult.query.filter(AutoResult.case == case).group_by():
        statistics['total'] += 1
        if result_instance.result is None:
            statistics['invalid'] += 1
        else:
            statistics[result_instance.result] += 1
    return jsonify(ret), 200
