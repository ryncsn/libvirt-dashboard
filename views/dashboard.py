import datetime
import re
from flask import Blueprint, Markup, render_template, request, jsonify
from model import db, AutoResult, ManualResult, refresh_result, Run
from flask import current_app as app

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

    # TODO: Remove it from here
    known_postfix = ['virtual_networks', 'virtual_disk', 'hooks', 'misc', 'migration', 'guest_kernel_debugging', 'console', 'virtio_rng', 'storage', 'secret', 'graphical_framebuffers', 'libvirtd', 'mem', 'managed_save', 'block_job_commit_pull','attach_detach_media', 'remote_access', 'attach_detach_interface', 'block_copy_no_shallow', 'virsh_domain', 'svirt', 'attach_detach_disk', 'guest_agent', 'snapshot', 'block_copy_shal, low', 'network_filter', 'cpu', 'numa']
    known_tags = ['Virtual networks','Virtual disks','hooks','','Migration','Guest kernel debugging','console and serial devices','Security','Storage','Virsh cmd - Confirmed','Graphical framebuffers','Libvirtd','Memory management','Managed save','Snapshot','Virtual disks','Remote access','Virtual networks','Snapshot','Virsh cmd - Confirmed','sVirt','Virtual disks','Guest agent','Snapshot','Snapshot','network filter','CPU Management','NUMA']

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

        tags = None
        if test_run.name.split('-')[-1] in known_postfix:
            tags = known_tags[known_postfix.index(test_run.name.split('-')[-1])]

        polaroin_testrun = Polarion.TestRunRecord(
            project=test_run.project,
            name=test_run.name,
            description="CI Job: " + str(test_run.description),
            type=test_run.type,
            date=test_run.date,
            build=test_run.build,
            version=test_run.version,
            arch=test_run.arch,
            tags=tags
        )

        try:
            for record in AutoResult.query.filter(AutoResult.run_id == test_run.id):
                try:
                    if not record.linkage_result:
                        raise ConflictError()
                except ConflictError:
                    if forced and record.error not in ["Unknown Issue", "Caselink Failure"]:
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
                if record.result not in ['passed', 'failed']:
                    if forced:
                        db.session.delete(record)
                        db.session.commit
                        continue
                    else:
                        error_runs.append(test_run.as_dict())
                        error_runs[-1]['reason'] = (
                            'Manual result %s contains error %s' % (record.case, record.result))
                        raise ConflictError()

                polaroin_testrun.add_record(
                    case=record.case,
                    result=record.result,
                    duration=record.time,
                    datetime=test_run.date,  # Datetime
                    executed_by='CI',
                    comment=record.comment
                )

            if len(polaroin_testrun.records) < 1:
                error_runs.append(test_run.as_dict())
                error_runs[-1]['reason'] = 'Too few manual results.'
                raise ConflictError()

        except ConflictError:
            continue

        with Polarion.PolarionSession() as session:
            polaroin_testrun.submit(session)

        #TODO issue a caselink backup

        test_run.submit_date = datetime.datetime.now()
        test_run.polarion_id = polaroin_testrun.test_run_id
        db.session.add(test_run)
        db.session.commit()
        submitted_runs.append(test_run.as_dict())

    return jsonify( {'submitted': submitted_runs, 'error': error_runs, })
