"""
API for datatable.
"""
import json

from sqlalchemy import func
from flask_restful import Resource, Api
from flask import Blueprint, request
from model import db, Run, Tag, AutoResult, ManualResult

dt_api = Blueprint('dt_api', __name__)

api = Api(dt_api)

class TestRunList(Resource):
    def get(self):
        draw = request.args.get('draw', None)
        start = request.args.get('start', None)
        length = request.args.get('length', None)
        search_value = request.args.get('search[value]')
        search_regex = request.args.get('search[regex]')
        #TODO: need something to decode a dt query properly.
        tags = request.args.get('columns[6][search][value]', '[]')
        auto_case = request.args.get('columns[3][search][value]', '[]')
        manual_case = request.args.get('columns[5][search][value]', '[]')
        cols = {
            '0': Run.date,
            '1': Run.id,
            '2': Run.date,
            '3': Run.submit_date,
        }
        order_col = request.args.get('order[0][column]', 'Run')
        order_dir = request.args.get('order[0][dir]', 'asc')
        order_col = cols.get(order_col, Run.date)

        if order_dir == 'asc':
            order = order_col.asc()
        else:
            order = order_col.desc()

        total = Run.query.count()

        filtered = Run.query
        if search_value:
            filtered = filtered.filter(Run.name.like("%%%s%%" % search_value))
        if search_regex:
            #TODO
            pass

        try:
            tags = json.loads(tags)
        except ValueError:
            return {
                'draw': draw,
                'recordsTotal': total,
                'recordsFiltered': 0,
                'data': [],
            }

        if tags:
            filtered = filtered.filter(Run.tags.any(Tag.name.in_(tags)))

        if auto_case:
            filtered = filtered.filter(Run.auto_results.any(AutoResult.case == auto_case))

        if manual_case:
            filtered = filtered.filter(Run.manual_results.any(ManualResult.case == manual_case))

        filtered = filtered.order_by(order)

        count = filtered.count()
        ret = []

        if start is not None:
            filtered = filtered.offset(start)
        if length is not None:
            filtered = filtered.limit(length)

        for run in filtered:
            ret.append(run.as_dict(detailed=True))

        return {
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': count,
            'data': ret,
            }

api.add_resource(TestRunList, '/run/', endpoint='test_run_list')
