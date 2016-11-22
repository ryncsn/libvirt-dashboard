"""
API for datatable.
"""
import json

from sqlalchemy import func
from flask_restful import Resource, Api
from flask import Blueprint, request
from model import db, Run, Tag

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
        tags = request.args.get('columns[7][search][value]', '[]')

        total = Run.query.count()

        filtered = Run.query
        if search_value:
            filtered = filtered.filter(Run.name.like("%%%s%%" % search_value))
        if search_regex:
            #TODO
            pass

        count = filtered.count()
        filtered = filtered.order_by(Run.date.desc())

        ret = []

        try:
            tags = json.loads(tags)
        except ValueError:
            return {
                'draw': draw,
                'recordsTotal': total,
                'recordsFiltered': count,
                'data': ret,
            }

        if tags:
            filtered = filtered.filter(Run.tags.any(Tag.name.in_(tags)))

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
