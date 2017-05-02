import datetime
from sqlalchemy import func
from celery import current_task

from .. import celery
from ..model import db, Tag, Run
from ..utils import polarion as Polarion

CHUNK_SIZE=256

def update_status(state, meta=None):
    """
    Update task status if running by a worker, else do nothing
    """
    direct_call = current_task.request.id is None
    if not direct_call:
        current_task.update_state(state=state, meta=meta)


@celery.task()
def submit_to_polarion(testrun_ids, forced=False):
    if not Polarion.PYLARION_INSTALLED:
        return

    def _gen_polarion_testrun(test_run):
        test_description = "Dashboard ID: %s<br> Tags: %s<br>" % (
            test_run.id, " ".join('"%s"' % t.name for t in test_run.tags.all()))

        polarion_tags = ", ".join(tag.name.lstrip("polarion:").strip()
                                  for tag in test_run.tags.filter(Tag.name.like("polarion:%"))
                                 ) or None

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
    try:
        # Read-only lock for updating rows
        for test_run in Run.query.with_for_update(read=True).filter(Run.id in testrun_ids):
            errors = test_run.blocking_errors(exclude="ALL") if forced else test_run.blocking_errors()
            re_submit = bool(test_run.submit_date)
            if errors:
                test_run.submit_status = errors
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

                    assert polarion_testrun.test_run_id
                except (Polarion.PolarionException, Polarion.PylarionLibException,
                        Polarion.SSLError, Polarion.WebFault) as error:
                    test_run.submit_status = error.message or str(error)
                else:
                    # No exception, means everything went well
                    test_run.submit_date = datetime.datetime.now()
                    test_run.polarion_id = polarion_testrun.test_run_id
                    test_run.submit_status = "Success"
    finally:
        # Always Release the lock
        db.session.commit()
