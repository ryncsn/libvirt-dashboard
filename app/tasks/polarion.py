import re
import datetime
from sqlalchemy import func
from celery import current_task
import traceback

from .. import celery
from ..model import db, Tag, Run
from ..utils import polarion as Polarion

from config import ActiveConfig

POLARION_URL = ActiveConfig.POLARION_URL
POLARION_USER = ActiveConfig.POLARION_USER
POLARION_PLANS = ActiveConfig.POLARION_PLANS
POLARION_PROJECT = ActiveConfig.POLARION_PROJECT
POLARION_PASSWORD = ActiveConfig.POLARION_PASSWORD

CHUNK_SIZE = 256


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

    def _gen_polarion_testrun(testrun):
        def get_nearest_plan(product, version, date):
            query = POLARION_PLANS["%s-%s" % (product, version)]
            return Polarion.get_nearest_plan_by_pylarion(query, date)

        testrun_description = "Dashboard ID: %s\n Tags: %s\n" % (
            testrun.id, " ".join('"%s"' % t.name for t in testrun.tags.all()))

        testrun_tags = ", ".join(tag.name.lstrip("polarion:").strip()
                                 for tag in testrun.tags.filter(Tag.name.like("polarion:%")) or [])

        testrun_properties = {}
        for test_property in testrun.properties.all():
            name, value = test_property.name, test_property.value
            group_name, prop_name = name.split('-', 1)
            prop_group = testrun_properties.setdefault(group_name, {})
            prop_group[prop_name] = value

        for group_name, group in testrun_properties.items():
            if group_name in ["package"]:
                testrun_description += "<table><tr><th>%s</th></tr>" % group_name.title()
                for name, value in group.items():
                    testrun_description += "<tr><td>%s</td><td>%s</td></tr>" % (name, value)
                testrun_description += "</table>"

        testrun_id = '{name} {framework} {build} {date} {extra}'.format(
            name=testrun.name,
            framework=testrun.framework,
            build=testrun.build,
            date=testrun.date.isoformat(),
            extra=" ".join([tag.name for tag in test_run.tags.all()])
        )

        testrun_id = re.sub(r'[.\/:*"<>|~!@#$?%^&\'*()+`,=]', '-', testrun_id)
        testrun_name = testrun_id

        testrun_record = Polarion.TestRunRecord(
            POLARION_PROJECT,
            testrun_name,

            # Custom fields
            description=testrun_description,
            assignee="kasong",
            plannedin=get_nearest_plan(testrun.product, testrun.version, testrun.date),
            isautomated=True,
            build=testrun.build,
            arch=testrun.arch,
            type=test_run.type,
            component=test_run.component,
            jenkinsjobs=test_run.ci_url,
            tags=testrun_tags
        )

        testrun_record.set_polarion_property("group-id", test_run.build)
        testrun_record.set_polarion_property("testrun-id", testrun_id)
        testrun_record.set_polarion_property("testrun-template-id", "libvirt-autotest")
        testrun_record.set_polarion_response("libvirt_dashboard_submitted", "true")
        testrun_record.set_polarion_response("libvirt_dashboard_id", test_run.id)
        testrun_record.set_polarion_response("polarion_testrun", testrun_id)
        testrun_record.set_polarion_response("libvirt_dashboard_build", test_run.build)

        return testrun_record

    try:
        # Read-only lock for updating rows
        query = Run.query.with_for_update(read=True).filter(Run.id.in_(testrun_ids))
        for test_run in query.all():
            test_run.submit_status = "Task running"
            errors = test_run.blocking_errors(exclude="ALL") if forced else test_run.blocking_errors()
            if errors:
                test_run.submit_status = "\n".join(errors)
            else:
                try:
                    polarion_testrun = _gen_polarion_testrun(test_run)
                    for record in test_run.manual_results:
                        polarion_result = record.result
                        if polarion_result in ['ignored', 'skipped']:
                            continue
                        if polarion_result not in ['passed', 'failed']:
                            polarion_result = 'blocked'

                        polarion_testrun.add_testcase(
                            case=record.case,
                            result=polarion_result,
                            comment=record.comment,
                            elapsed_sec=record.time,
                        )

                    res = polarion_testrun.submit()
                    if res:
                        raise Exception(str(res))

                except Exception as error:
                    test_run.submit_status = (
                        "Failed: %s: %s" % (type(error), error.message or str(error))
                    )  # TODO
                    if hasattr(error, "__traceback__"):
                        traceback.print_tb(error.__traceback__)
                    else:
                        traceback.print_exc()
                    # TODO: Error Detail

                else:
                    # No exception, means everything went well
                    test_run.polarion_id = polarion_testrun.get_polarion_property('testrun-id')
                    test_run.submit_status = "Waiting For Feedback"
    finally:
        # Always Release the lock
        query.session.commit()
