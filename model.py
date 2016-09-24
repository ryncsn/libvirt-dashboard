import re
import caselink as CaseLink
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import validates, load_only
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
from requests import HTTPError, ConnectionError


db = SQLAlchemy()


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


class Run(db.Model):
    __tablename__ = 'run'
    __table_args__ = (
        db.UniqueConstraint('name', 'type', 'build', 'version', 'arch', 'date',
                            name='_test_run_id_uc'),
        {'sqlite_autoincrement': True},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=False, nullable=False)
    component = db.Column(db.String(255), unique=False, nullable=False)
    build = db.Column(db.String(255), unique=False, nullable=False)
    product = db.Column(db.String(255), unique=False, nullable=False)
    version = db.Column(db.String(255), unique=False, nullable=False)
    arch = db.Column(db.String(255), unique=False, nullable=False)
    type = db.Column(db.String(255), unique=False, nullable=False)
    framework = db.Column(db.String(255), unique=False, nullable=False)
    project = db.Column(db.String(255), unique=False, nullable=False)
    date = db.Column(db.DateTime(), unique=False, nullable=False)

    ci_url = db.Column(db.String(1024), unique=False, nullable=False)
    description = db.Column(db.Text(), unique=False, nullable=True)

    auto_results = db.relationship('AutoResult', back_populates='run', lazy='dynamic')
    manual_results = db.relationship('ManualResult', back_populates='run', lazy='dynamic')
    submit_date = db.Column(db.DateTime(), unique=False, nullable=True)
    polarion_id = db.Column(db.String(1024), unique=False, nullable=True)

    def __repr__(self):
        return '<TestRun %s>' % self.name

    def __init__(self, **run):
        for key, value in run.iteritems():
            setattr(self, key, value)

    def get_statistics(self):
        ret = {
            'auto_passed': 0,
            'auto_failed': 0,
            'auto_skipped': 0,
            'auto_error': 0,
            'manual_passed': 0,
            'manual_failed': 0,
            'manual_error': 0,
        }
        for result in self.auto_results\
                      .options(load_only("output", "failure", "skip", "linkage_result"))\
                      .all():
            if result.result == 'passed':
                ret['auto_passed'] += 1
            elif result.result == 'failed':
                ret['auto_failed'] += 1
            elif result.result == 'skipped':
                ret['auto_skipped'] += 1

            if result.linkage_result is None:
                ret['auto_error'] += 1
            if result.linkage_result is 'ignored':
                ret['auto_ignored'] += 1

        for result in self.manual_results\
                      .options(load_only("result"))\
                      .all():
            if result.result == 'failed':
                ret['manual_failed'] += 1
            elif result.result == 'passed':
                ret['manual_passed'] += 1
            elif result.result == 'incomplete':
                ret['manual_error'] += 1
        return ret

    def as_dict(self, detailed=False):
        ret = {}
        for c in self.__table__.columns:
            if c.name != 'date':
                ret[c.name] = getattr(self, c.name)
        ret['date'] = self.date.isoformat()
        if self.submit_date:
            ret['submit_date'] = self.submit_date.isoformat()
        ret['polarion_id'] = self.polarion_id
        if detailed:
            ret.update(self.get_statistics())
        return ret


class AutoResult(db.Model):
    __tablename__ = 'auto_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='auto_results')

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), nullable=False)
    skip = db.Column(db.String(65535), nullable=True)
    failure = db.Column(db.String(65535), nullable=True)
    output = db.Column(db.Text(), nullable=True)
    source = db.Column(db.Text(), nullable=True)
    comment = db.Column(db.String(65535), nullable=True)

    # If bugs is not None, manualcases means cases failed
    # If bugs is None, manualcases means cases passed
    # If error is not None, dashboard faild to look up bug/cases for this autocase
    error = db.Column(db.String(255), nullable=True)
    linkage_result = db.Column(db.String(255), nullable=True)

    @hybrid_property
    def result(self):
        if self.skip:
            return 'skipped'
        if self.failure:
            return 'failed'
        if self.output:
            return 'passed'
        return None

    @validates('error')
    def validate_error(self, key, result):
        assert result in ['No Caselink', 'No Linkage', 'Unknown Issue', 'Caselink Failure', None, ]
        return result

    @validates('linkage_result')
    def validate_linkage_result(self, key, result):
        assert result in ['ignored', 'skipped', 'passed', 'failed', None, ]
        return result

    @validates('result')
    def validate_result(self, key, result):
        assert result in ['skipped', 'passed', 'failed', None, ]
        return result

    def __repr__(self):
        return '<TestResult %s-%s>' % (self.run_id, self.case)

    def __init__(self, **result):
        for key, value in result.iteritems():
            setattr(self, key, value)

    def as_dict(self, detailed=False):
        ret = {}
        for c in self.__table__.columns:
            if c.name not in ['date', 'output']:
                ret[c.name] = getattr(self, c.name)
        ret['result'] = self.result
        if not detailed:
            ret['output'] = 'Not showing'
        else:
            ret['output'] = self.output
        return ret


class ManualResult(db.Model):
    __tablename__ = 'manual_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='manual_results')

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), default=0.0, nullable=False)
    comment = db.Column(db.String(65535), nullable=True)

    result = db.Column(db.String(255), nullable=True)

    @validates('result')
    def validate_result(self, key, result):
        assert result in ['passed', 'failed', 'incomplete', ]
        return result

    def __repr__(self):
        return '<ManualCaseResult %s-%s: %s>' % (self.run_id, self.case, self.result)

    def __init__(self, **result):
        for key, value in result.iteritems():
            setattr(self, key, value)

    def as_dict(self, detailed=False):
        ret = {}
        for c in self.__table__.columns:
            ret[c.name] = getattr(self, c.name)
        return ret


def _update_manual(autocase, manualcase_id, session,
                   expected_results=None, from_results=None, to_result=None, comment=''):
    """
    Update a ManualResult.
    Change it's current result as needed and update its duration time.

    :param expected_results: Acceptable current result value, eg: ['incomplete', None],
        if ManualResult in not in any of the given state, will return None and touch nothing.

    :param from_results: Acceptable current result value, eg: ['incomplete', None],
        if ManualResult in not in any of the given state, will only accumulate it's duration time
        otherwise, will change it's result to 'to_result'

    :param to_result: New result value.
    """
    manualcase = get_or_create(session, ManualResult, run_id=autocase.run_id, case=manualcase_id)
    if expected_results:
        if not manualcase.result in expected_results:
            #print "expected + " + str(expected_results)+ "get "+ str(manualcase.result)
            return None
    if to_result:
        if not from_results or manualcase.result in from_results:
            manualcase.result = to_result
        else:
            #print "expected + " + str(from_results)+ "get "+str(manualcase.result)
            pass
    manualcase.time += float(autocase.time)
    if not manualcase.comment:
        manualcase.comment = comment
    else:
        manualcase.comment += "\n" + comment
    return manualcase


def gen_manual_case(result, caselink, session):
    """
    Take a Autocase result instance, generate it's ralated manual cases.

    Need to clean all manual cases for a test run first.
    """

    if not caselink:
        return (False, "No caselink")

    if result.result == 'skipped' or result.result == 'ignored':
        if not caselink.manualcases or len(caselink.manualcases) == 0:
            return (False, "No manual case for skipped auto case")
        for caselink_manualcase in caselink.manualcases:
            if not _update_manual(result, caselink_manualcase.id, session,
                                  expected_results = [None, 'incomplete', 'failed'],
                                  from_results = [None], to_result = 'incomplete',
                                  comment = ('Skipped Auto case: "%s"\n' % result.case)):
                #print "Skip for non incomplete case"
                pass
        return (True, "Manual case updated.")

    elif result.result == 'failed':
        # Auto Case failed with message <result['failure']>
        if not caselink.failures or len(caselink.failures) == 0:
            return (False, "No manual case for failed auto case")
        for failure in caselink.failures:
            if re.match(failure.failure_regex, result.failure) is not None:
                for case in failure.manualcases:
                    if not _update_manual(result, case.id, session,
                                          expected_results = [None, 'incomplete', 'failed'],
                                          from_results = [None, 'incomplete'], to_result = 'failed',
                                          comment = ('Failed auto case: "%s", BUG: "%s"\n' %
                                                     (failure.bug.id, result.case))):
                        #print "Failed for non incomplete case"
                        pass
        return (True, "Manual Case marked failed.")

    elif result.result == 'passed':
        if not caselink.manualcases or len(caselink.manualcases) == 0:
            return (False, "No manual case for passed auto case")
        for caselink_manualcase in caselink.manualcases:
            ManualCasePassed=True
            for related_autocase in caselink_manualcase.autocases:
                related_result = AutoResult.query.get((result.run_id, related_autocase.id))
                if not related_result and related_autocase != caselink:
                    # This auto case passed, but some related auto case are not submitted yet.
                    ManualCasePassed = False
                    if not _update_manual(result, caselink_manualcase.id, session,
                                          expected_results = [None, 'incomplete', 'failed'],
                                          from_results = [None], to_result = 'incomplete',
                                          comment = ('Passed Auto case: "%s"\n' % result.case)):
                        #print "Incomplete case makred passed"
                        pass
                    break

                elif related_result.skip is not None:
                    # This auto case passed, but some related auto case are skipped.
                    ManualCasePassed = False
                    if not _update_manual(result, caselink_manualcase.id, session,
                                          expected_results = [None, 'incomplete', 'failed'],
                                          from_results = [None], to_result = 'incomplete',
                                          comment = ('Passed Auto case: "%s"\n' % result.case)):
                        #print "Skipped case makred passed"
                        pass
                    break

                elif related_result.failure is not None:
                    # This auto case passed, but some related auto case are failed.
                    ManualCasePassed = False
                    if not _update_manual(result, caselink_manualcase.id, session,
                                          expected_results = [None, 'failed'],
                                          from_results = [None], to_result = 'incomplete',
                                          comment = ('Passed Auto case: "%s"\n' % result.case)):
                        #print "Manual already failed, not properly marked"
                        pass
                    break

            if ManualCasePassed:
                # This auto case passed, and all related auto case are passed.
                if not _update_manual(result, caselink_manualcase.id, session,
                                      expected_results = [None, 'incomplete'],
                                      from_results = [None, 'incomplete'], to_result = 'passed',
                                      comment = ('Passed Auto case: "%s"\n' % result.case)):
                    #print "Trying to pass already failed case"
                    pass
        return (True, "Manual Case updated.")


def refresh_result(result, session, gen_manual=True, gen_error=True, gen_result=True):
    """
    Take a AutoResult instance, rewrite it's error and linkage_result
    with data in caselink.
    """
    # Failed -> look up in failures, if any bug matches, mark manualcase failed
    # Passed -> look up in linkages(manualcases), if all related autocase of a manualcase
    #           passed, mark the manualcase passed
    # Mark error when lookup failed
    if gen_error:
        result.error = None
    if gen_result:
        result.linkage_result = None

    def _set_error(err):
        if gen_error:
            result.error = err

    def _set_result(res):
        if gen_result:
            result.linkage_result = res

    try:
        this_autocase = CaseLink.AutoCase(result.case).refresh()
    except (HTTPError, ConnectionError) as err:
        if hasattr(err, 'status_code') and err.response.status_code == 404:
            _set_error('No Caselink')
        else:
            _set_error('Caselink Failure')
        return False, result.error

    if result.skip:
        _set_result('skipped')

    elif result.failure:
        # Auto Case failed with message <result['failure']>
        bug_exists = False
        for failure in this_autocase.failures:
            if re.match(failure.failure_regex, result.failure) is not None:
                bug_exists = True
                _set_result('failed')

        if not bug_exists:
            _set_error('Unknown Issue')

    elif result.output:
        if not this_autocase.manualcases or len(this_autocase.manualcases) == 0:
            _set_error('No Linkage')
        else:
            _set_result('passed')

    if not result.linkage_result:
        return False, result.error

    else:
        if gen_manual:
            return gen_manual_case(result, this_autocase, session)
        else:
            return True, result.linkage_result
