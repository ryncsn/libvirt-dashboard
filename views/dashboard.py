import re
import datetime
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, jsonify
from flask import current_app as app
from model import db, AutoResult, ManualResult, LinkageResult, Run

try:
    import utils.polarion as Polarion
    from suds import WebFault
    from ssl import SSLError
    from utils.polarion import PolarionException
    from pylarion.exceptions import PylarionLibException
    PYLARION_INSTALLED = True
except ImportError:
    PYLARION_INSTALLED = False

dashboard = Blueprint('dashboard', __name__)


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
                           ajax='/api/run/' + str(run_id) + '/auto/')


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
@dashboard.route('/trigger/run/submit/<string:regex>', methods=['GET'])
@dashboard.route('/trigger/run/<int:run_id>/submit', methods=['GET'])
def submit_to_polarion(run_id=None, regex=None):
    forced = (request.args.get('forced', False) == "true")

    if not PYLARION_INSTALLED:
        return jsonify({'message': 'Pylarion not installed, you need to\
                        install it manually or Pylarion support is disabled.'}), 200
    if not app.config['POLARION_ENABLED']:
        return jsonify({'message': 'Polarion not enabled, please contract the admin.'}), 200

    def _get_testruns_to_submit():
        test_runs = Run.query.filter(Run.id == run_id) if run_id else Run.query.filter()
        for test_run in test_runs:
            if regex:
                if not re.match(regex, test_run.name):
                    continue
            yield test_run

    def _gen_polarion_testrun(test_run):
        test_description = "Dashboard ID: %s<br> Tags: %s<br>" % (
            test_run.id, " ".join('"%s"' % t.name for t in test_run.tags.all()))

        polarion_tags = []
        for tag in test_run.tags.all():
            if tag.name.startswith("polarion:"):
                polarion_tags.append(tag.name.lstrip("polarion:").strip())
        polarion_tags = ", ".join(polarion_tags) or None

        test_properties = {}
        for test_property in test_run.properties.all():
            name, value = test_property.name, test_property.value
            group_name, prop_name = name.split('-', 1)
            test_property_group = test_properties.setdefault(group_name, {})
            test_property_group[prop_name] = value

        for group_name, group in test_properties.items():
            if group_name in ["package"]:
                test_description += "<table><tr><th>%s</th></tr>" % group_name.title()
                for name, value in group.items():
                    test_description += "<tr><td>%s</td><td>%s</td></tr>" % (name, value)
                test_description += "</table>"

        return Polarion.TestRunRecord(
            dashboard_id=test_run.id,
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

    submitted_runs, error_runs = [], []

    for test_run in _get_testruns_to_submit():
        errors = test_run.blocking_errors(exclude="ALL") if forced else test_run.blocking_errors()
        re_submit = bool(test_run.submit_date)
        if errors:
            error_runs.append({'name': test_run.short_unique_name(), 'reason': errors})
        else:
            try:
                polarion_testrun = _gen_polarion_testrun(test_run)
                for record in test_run.manual_results:
                    polarion_result = record.result
                    if polarion_result in ['ignored', 'skipped']:
                        continue
                    if polarion_result not in ['passed', 'failed']:
                        polarion_result = 'blocked'

                    polarion_testrun.add_record(
                        case=record.case,
                        result=polarion_result,
                        duration=record.time,
                        record_datetime=test_run.date,  # Datetime
                        executed_by='CI',
                        comment=record.comment
                    )

                with Polarion.PolarionSession() as session:
                    polarion_testrun.submit(session, resubmit=re_submit)

                #TODO issue a caselink backup
                test_run.submit_date = datetime.datetime.now()
                test_run.polarion_id = polarion_testrun.test_run_id
                db.session.add(test_run)
                db.session.commit()
                submitted_runs.append(test_run.short_unique_name())

            except (PolarionException, PylarionLibException, SSLError, WebFault) as error:
                error_runs.append({'name': test_run.short_unique_name(), 'reason': error.message})

    return jsonify( {'submitted': submitted_runs, 'not_submitted': error_runs, })
