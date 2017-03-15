from flask import render_template, make_response, Blueprint
from model import Run, AutoResult, ManualResult

table = Blueprint('table', __name__)

def column_to_table(model, ajax_url, code, extra_column=None):
    """
    Render array of entrys of a database with datatable.
    Array should contain dicts with the same keys.
    """
    columns = model.__table__.columns
    columns = [str(col).split('.')[-1] for col in columns]
    if extra_column:
        columns += extra_column
    resp = make_response(render_template('column_table.html',
                                         column_names=columns,
                                         column_datas=columns,
                                         ajax=ajax_url), code)
    return resp


@table.route('/run/', methods=['GET'])
def test_run_table():
    return column_to_table(
        Run,
        '/api/run/',
        200)

@table.route('/run/<int:run_id>/auto/', methods=['GET'])
def auto_result_table(run_id):
    return column_to_table(
        AutoResult,
        '/api/run/' + str(run_id) + '/auto/',
        200)

@table.route('/run/<int:run_id>/manual/', methods=['GET'])
def manual_result_table(run_id):
    return column_to_table(
        ManualResult,
        '/api/run/' + str(run_id) + '/manual/',
        200)
