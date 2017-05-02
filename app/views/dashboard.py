import re
import datetime
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, jsonify
from flask import current_app as app

from ..model import db, AutoResult, ManualResult, LinkageResult, Run, Tag
from ..tasks import submit_to_polarion as submit_to_polarion_task

from ..utils.polarion import PYLARION_INSTALLED

dashboard = Blueprint('dashboard', __name__)

CHUNK_SIZE=128


@dashboard.route('/', methods=['GET'])
def index():
    return render_template('testrun_overview.html')


@dashboard.route('/diff', methods=['GET'])
def testrun_diff():
    return render_template('testrun_diff.html')


@dashboard.route('/dashboard', methods=['GET'])
def testrun_dashboard():
    return render_template('testrun_dashboard.html')


@dashboard.route('/resolve/run/<int:run_id>/auto/', methods=['GET'])
def resolve_autocase(run_id):
    return render_template('resolve_auto.html',
                           ajax='/api/run/' + str(run_id) + '/auto/',
                           run_id=run_id)


@dashboard.route('/resolve/run/<int:run_id>/manual/', methods=['GET'])
def resolve_manualcase(run_id):
    return render_template('resolve_manual.html',
                             ajax='/api/run/' + str(run_id) + '/manual/')


@dashboard.route('/trigger/run/<int:run_id>/refresh', methods=['GET'])
def refresh_testrun(run_id):
    LinkageResult.query.filter(LinkageResult.run_id == run_id).\
            delete(synchronize_session=False)
    ManualResult.query.filter(ManualResult.run_id == run_id).\
            delete(synchronize_session=False)
    AutoResult.query.filter(
        AutoResult.run_id == run_id,
        AutoResult.output == None,
        AutoResult.failure == None,
        AutoResult.skip == None).\
        delete(synchronize_session=False)

    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        result_instance.refresh_result()
        result_instance.gen_linkage_result(session=db.session)
        result_instance.refresh_comment()
        db.session.add(result_instance)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    return jsonify({'message': 'done'}), 200


@dashboard.route('/trigger/run/<int:run_id>/auto/<string:case>/refresh', methods=['GET'])
@dashboard.route('/trigger/run/<int:run_id>/auto/refresh', methods=['GET'])
def refresh_auto(run_id, case=None):
    gen_error = request.args.get('error', False) == 'true'
    gen_result = request.args.get('result', False) == 'true'
    if case:
        query = AutoResult.query.filter(AutoResult.run_id == run_id, AutoResult.case == case)
    else:
        query = AutoResult.query.filter(AutoResult.run_id == run_id)

    for result_instance in query:
        result_instance.refresh_result()
        result_instance.gen_linkage_result(db.session, gen_manual=False)
        result_instance.refresh_comment()

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500
    return jsonify({'message': 'success'}), 200


@dashboard.route('/trigger/run/<int:run_id>/manual/refresh', methods=['GET'])
def refresh_manual(run_id):
    ManualResult.query.filter(ManualResult.run_id == run_id).\
            delete(synchronize_session=False)

    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        result_instance.gen_linkage_result(db.session, gen_manual=False)
        result_instance.refresh_comment()

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    return jsonify({'message': 'success'}), 200


@dashboard.route('/trigger/run/submit', methods=['GET'])
@dashboard.route('/trigger/run/submit/<string:run_regex>', methods=['GET'])
@dashboard.route('/trigger/run/<int:run_id>/submit', methods=['GET'])
def submit_to_polarion(run_id=None, run_regex=None):
    forced = (request.args.get('forced', False) == "true")

    if not PYLARION_INSTALLED:
        return jsonify({'message': 'Pylarion not installed, you need to\
                        install it manually or Pylarion support is disabled.'}), 503

    if not app.config['POLARION_ENABLED']:
        return jsonify({'message': 'Polarion not enabled, please contract the admin.'}), 503

    if run_id:
        test_runs = Run.query.filter(Run.id == run_id)
    elif run_regex:
        test_runs = Run.query.filter(Run.name.op("REGEXP", run_regex)).yield_per(CHUNK_SIZE)

    if test_runs.count() == 0:
        return jsonify({'message': 'No matching test runs founded'}), 403

    test_runs.update({Run.submit_status: "Pending"})

    db.session.commit()

    submit_to_polarion_task.delay([run.id for run in test_runs], forced)

    return jsonify({'message': 'Tasks queued'}), 200
