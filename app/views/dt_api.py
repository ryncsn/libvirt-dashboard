"""
API for datatable.
"""
import json

from sqlalchemy import func
from flask_restful import Resource, Api
from flask import Blueprint, request

from ..model import db, Run, Tag, AutoResult, ManualResult

dt_api = Blueprint('dt_api', __name__)

api = Api(dt_api)

class TestRunList(Resource):
    def get(self):
        draw = request.args.get('draw', None)
        start = request.args.get('start', None)
        length = request.args.get('length', None)
        search_value = request.args.get('search[value]')
        search_regex = request.args.get('search[regex]')

        submit_status = request.args.get('submitStatus', '')
        contains_autocase = request.args.get('containsAutocases', '')
        contains_manualcase = request.args.get('containsManualcases', '')
        has_tags = request.args.get('hasTags', '[]')

        order_col = {
            '0': Run.id,
            '1': Run.date,
            '2': Run.submit_date,
        }.get(request.args.get('order[0][column]', '0'), Run.date)

        order_dir = request.args.get('order[0][dir]', 'asc') == 'asc' and 'asc' or 'desc'

        order = getattr(order_col, order_dir)()

        total = Run.query.count()

        filtered = Run.query
        if search_value:
            filtered = filtered.filter(Run.name.like("%%%s%%" % search_value))
        if search_regex:
            #TODO
            pass

        try:
            tags = json.loads(has_tags)
        except ValueError:
            return {
                'draw': draw,
                'recordsTotal': total,
                'recordsFiltered': 0,
                'data': [],
            }

        if tags:
            filtered = filtered.filter(Run.tags.any(Tag.name.in_(tags)))

        if contains_autocase:
            filtered = filtered.filter(Run.auto_results.any(AutoResult.case == contains_autocase))

        if contains_manualcase:
            filtered = filtered.filter(Run.manual_results.any(ManualResult.case == contains_manualcase))

        if submit_status:
            if submit_status == 'all':
                pass
            elif submit_status == 'notsubmitted':
                filtered = filtered.filter(Run.submit_date == None)
            elif submit_status == 'submitted':
                filtered = filtered.filter(Run.submit_date != None)

        filtered = filtered.order_by(order)

        count = filtered.count()
        ret = []

        if start is not None:
            filtered = filtered.offset(start)
        if length is not None:
            filtered = filtered.limit(length)

        for run in filtered:
            ret.append(run.as_dict(statistics=True))
            db.session.commit()

        return {
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': count,
            'data': ret,
        }

api.add_resource(TestRunList, '/run/', endpoint='test_run_list')
