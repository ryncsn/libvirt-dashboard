"""
API for datatable.
"""
from sqlalchemy import func
from flask_restful import Resource, Api
from flask import Blueprint, request
from model import db, Run

dt_api = Blueprint('dt_api', __name__)

api = Api(dt_api)

class TestRunList(Resource):
    def get(self):
        draw = request.args.get('draw', None)
        start = request.args.get('start', None)
        length = request.args.get('length', None)
        search_value = request.args.get('search[value]')
        search_regex = request.args.get('search[regex]')

        total = Run.query.count()

        filted = Run.query
        if search_value:
            filted = filted.filter(Run.name.like("%%%s%%" % search_value))
        if search_regex:
            #TODO
            pass
        count = filted.count()
        filted = filted.order_by(Run.date.desc())

        if start is not None:
            filted = filted.offset(start)
        if length is not None:
            filted = filted.limit(length)

        ret = []
        for run in filted:
            ret.append(run.as_dict(detailed=True))

        return {
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': count,
            'data': ret,
            }

api.add_resource(TestRunList, '/run/', endpoint='test_run_list')
