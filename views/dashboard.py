import re
import datetime
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, jsonify
from flask import current_app as app
from model import db, AutoResult, ManualResult, refresh_result, Run

try:
    import utils.polarion as Polarion
    PYLARION_INSTALLED = True
except ImportError:
    PYLARION_INSTALLED = False

dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/', methods=['GET'])
def index():
    return render_template('testrun_overview.html')


@dashboard.route('/dashboard', methods=['GET'])
def testrun_dashboard():
    return render_template('testrun_dashboard.html')


@dashboard.route('/resolve/run/<int:run_id>/auto/', methods=['GET'])
def resolve_autocase(run_id):
    columns = ["case", "time", "result", "error", "linkage_result"]
    return render_template('resolve_auto.html',
                           column_names=columns,
                           column_datas=columns,
                           ajax='/api/run/' + str(run_id) + '/auto/')


@dashboard.route('/resolve/run/<int:run_id>/manual/', methods=['GET'])
def resolve_manualcase(run_id):
    columns = ["case", "time", "comment", "result"]
    return render_template('resolve_manual.html',
                             column_names=columns,
                             column_datas=columns,
                             ajax='/api/run/' + str(run_id) + '/manual/')


@dashboard.route('/trigger/run/<int:run_id>/refresh', methods=['GET'])
def refresh_testrun(run_id):
    ret = {}
    ManualResult.query.filter(ManualResult.run_id == run_id).\
            delete(synchronize_session=False)

    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        (success, message) = refresh_result(result_instance, db.session)
        db.session.add(result_instance)
        if not success:
            ret[result_instance.case] = message

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    if len(ret.keys()) == 0:
        return jsonify({'message': 'success'}), 200
    return jsonify(ret), 200


@dashboard.route('/trigger/run/<int:run_id>/auto/<string:case>/refresh', methods=['GET'])
@dashboard.route('/trigger/run/<int:run_id>/auto/refresh', methods=['GET'])
def refresh_auto(run_id, case=None):
    gen_error = request.args.get('error', False)
    gen_result = request.args.get('result', False)

    if gen_error == 'true':
        gen_error = True
    else:
        gen_error = False

    if gen_result == 'true':
        gen_result = True
    else:
        gen_result = False

    fail_message = {}
    if case:
        query = AutoResult.query.filter(AutoResult.run_id == run_id, AutoResult.case == case)
    else:
        query = AutoResult.query.filter(AutoResult.run_id == run_id)

    for result_instance in query:
        (success, message) = refresh_result(result_instance, db.session,
                                            gen_error = gen_error,
                                            gen_result = gen_result,
                                            gen_manual = True)
        db.session.add(result_instance)
        if not success:
            fail_message[result_instance.case] = message

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    if len(fail_message.keys()) == 0:
        return jsonify({'message': 'success'}), 200
    return jsonify(fail_message), 200


@dashboard.route('/trigger/run/<int:run_id>/manual/refresh', methods=['GET'])
def refresh_manual(run_id):
    fail_message = {}
    ManualResult.query.filter(ManualResult.run_id == run_id).\
            delete(synchronize_session=False)

    for result_instance in AutoResult.query.filter(AutoResult.run_id == run_id):
        (success, message) = refresh_result(result_instance, db.session, gen_error=False, gen_result=False)
        db.session.add(result_instance)
        if not success:
            fail_message[result_instance.case] = message

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'message': 'db error'}), 500

    if len(fail_message.keys()) == 0:
        return jsonify({'message': 'success'}), 200
    return jsonify(fail_message), 200


@dashboard.route('/trigger/run/submit', methods=['GET'])
@dashboard.route('/trigger/run/submit/<string:regex>', methods=['GET'])
@dashboard.route('/trigger/run/<int:run_id>/submit', methods=['GET'])
def submit_to_polarion(run_id=None, regex=None):
    forced = (request.args.get('forced', False) == "true")
    refresh = (request.args.get('refresh', False) == "true")

    if not PYLARION_INSTALLED:
        return jsonify({'message': 'Pylarion not installed, you need to\
                        install it manually or Pylarion support is disabled.'}), 200
    if not app.config['POLARION_ENABLED']:
        return jsonify({'message': 'Polarion not enabled, please contract the admin.'}), 200
    submitted_runs = []
    error_runs = []
    class ConflictError(Exception):
        pass

    if run_id:
        test_runs = Run.query.filter(Run.submit_date == None, Run.id == run_id)
    else:
        test_runs = Run.query.filter(Run.submit_date == None)

    for test_run in test_runs:
        if regex:
            if not re.match(regex, test_run.name):
                continue

        if refresh:
            ManualResult.query.filter(ManualResult.run_id == test_run.id)\
                    .delete(synchronize_session=False)
            db.session.commit()

            for result_instance in AutoResult.query.filter(AutoResult.run_id == test_run.id):
                (success, message) = refresh_result(result_instance, db.session,
                                                    gen_manual=True,
                                                    gen_error=True,
                                                    gen_result=True)
                db.session.add(result_instance)
            db.session.commit()

        polarion_tags = None
        for tag in test_run.tags.all():
            if tag.name.startswith("polarion-"):
                polarion_tags = tag.name.lstrip("polarion-")

        test_description = "Dashboard ID: %s<br>" % (test_run.id)
        test_description += "Tags: %s<br>" % " ".join('"%s"' % t.name for t in test_run.tags.all())

        test_properties = {}
        for test_property in test_run.properties:
            name, value = test_property.name, test_property.value
            test_property_group = test_properties.setdefault(name.split('-', 1)[0], {})
            test_property_group[name.split('-', 1)[1]] = value

        for group_name, group in test_properties.items():
            if group_name in ["package"]:
                test_description += "<table><tr><th>%s</th></tr>" % group_name.title()
                for name, value in group.items():
                    test_description += "<tr><td>%s</td><td>%s</td></tr>" % (name, value)
                test_description += "</table>"

        polarion_testrun = Polarion.TestRunRecord(
            d_id=test_run.id,
            name=test_run.name,
            component=test_run.component,
            build=test_run.build,
            product=test_run.product,
            version=test_run.version,
            arch=test_run.arch,
            type=test_run.type,
            framework=test_run.framework,
            project=test_run.project,
            date=test_run.date,
            ci_url=test_run.ci_url,
            description=test_description,
            title_tags=[tag.name for tag in test_run.tags.all()],
            polarion_tags=polarion_tags
        )

        try:
            for record in AutoResult.query.filter(AutoResult.run_id == test_run.id):
                try:
                    if not record.linkage_result:
                        raise ConflictError()
                except ConflictError:
                    if forced and record.error not in [
                            "Caselink Failure", "Unknown Issue", "No Caselink"]:
                        record.linkage_result = 'ignored'
                        db.session.add(record)
                        continue
                    else:
                        error_runs.append(test_run.as_dict())
                        # TODO: list all errors
                        error_runs[-1]['reason'] = (
                            'Auto result %s contains error %s' % (record.case, record.error))
                        raise ConflictError()

            for record in ManualResult.query.filter(ManualResult.run_id == test_run.id):
                polarion_result = record.result
                if polarion_result not in ['passed', 'failed']:
                    if forced:
                        polarion_result = 'blocked'
                    else:
                        error_runs.append(test_run.as_dict())
                        error_runs[-1]['reason'] = (
                            'Manual result %s contains error %s' % (record.case, record.result))
                        raise ConflictError()

                polarion_testrun.add_record(
                    case=record.case,
                    result=polarion_result,
                    duration=record.time,
                    record_datetime=test_run.date,  # Datetime
                    executed_by='CI',
                    comment=record.comment
                )

            if len(polarion_testrun.records) < 1:
                error_runs.append(test_run.as_dict())
                error_runs[-1]['reason'] = 'Too few manual results.'
                raise ConflictError()

        except ConflictError:
            db.session.rollback()
            continue

        with Polarion.PolarionSession() as session:
            polarion_testrun.submit(session)

        #TODO issue a caselink backup

        test_run.submit_date = datetime.datetime.now()
        test_run.polarion_id = polarion_testrun.test_run_id
        db.session.add(test_run)
        db.session.commit()
        submitted_runs.append(test_run.as_dict())

    return jsonify( {'submitted': submitted_runs, 'error': error_runs, })
