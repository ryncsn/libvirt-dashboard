import re
import caselink as CaseLink
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, load_only
from sqlalchemy import func, ForeignKeyConstraint
from flask_sqlalchemy import SQLAlchemy
from requests import HTTPError, ConnectionError


db = SQLAlchemy()


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance, True


run_tags_table = \
        db.Table('test_run_tags',
                 db.Column('run_id', db.Integer, db.ForeignKey('run.id')),
                 db.Column('tag_name', db.String(255), db.ForeignKey('tag.name'))
                )


class Property(db.Model):
    __tablename__ = 'property'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='properties', single_parent=True)

    name = db.Column(db.String(255), nullable=False, primary_key=True)
    value = db.Column(db.String(65535), nullable=False)

    def __repr__(self):
        return '<Property of Run: %s, %s:%s>' % (self.run_id, self.name, self.desc)

    def __init__(self, run_id=None, name=None, value=None):
        self.run_id = run_id
        self.name = name
        self.value = value


class Tag(db.Model):
    __tablename__ = 'tag'

    runs = db.relationship('Run', secondary=run_tags_table, back_populates='tags', lazy='dynamic')
    name = db.Column(db.String(255), nullable=False, primary_key=True)
    desc = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return '<Tag %s, Description:(%s)>' % (self.name, self.desc)

    def __init__(self, name, desc=None):
        self.name = name
        self.desc = desc


class Run(db.Model):
    __tablename__ = 'run'
    __table_args__ = (
        db.UniqueConstraint('name', 'date', name='_test_run_id_uc'),
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

    ci_url = db.Column(db.String(65535), unique=False, nullable=False)
    description = db.Column(db.Text(), unique=False, nullable=True)

    tags = db.relationship('Tag', secondary=run_tags_table, back_populates='runs', lazy='dynamic')
    properties = db.relationship('Property', back_populates='run', lazy='dynamic')

    submit_date = db.Column(db.DateTime(), unique=False, nullable=True)
    polarion_id = db.Column(db.String(1024), unique=False, nullable=True)

    auto_results = db.relationship('AutoResult', back_populates='run', lazy='dynamic')
    manual_results = db.relationship('ManualResult', back_populates='run', lazy='dynamic')
    linkage_results = db.relationship("LinkageResult", back_populates="run", cascade="all, delete")

    def __repr__(self):
        return '<TestRun %s>' % self.name

    def __init__(self, **run):
        self.update(**run)

    def update(self, **kwargs):
        """
        Update test run's tags and properties.
        """
        tags = None
        properties = None
        with db.session.no_autoflush:
            # Create relationship after other values are processed
            # to prevent IntegrityError caused by auto commit.
            for key, value in kwargs.items():
                if key == 'tags':
                    tags = value
                elif key == 'properties':
                    properties = value
                else:
                    setattr(self, key, value)
            if tags:
                for tag in tags:
                    tag_instance, _ = get_or_create(db.session, Tag, name=tag)
                    self.tags.append(tag_instance)
            if properties:
                for name, value in properties.items():
                    prop_instance = Property(name=name, value=value)
                    self.properties.append(prop_instance)

    def get_statistics(self):
        ret = {
            'auto_passed': 0,
            'auto_failed': 0,
            'auto_skipped': 0,
            # TODO: 'auto_error': 0,
            'manual_passed': 0,
            'manual_failed': 0,
            'manual_error': 0,
        }
        for result in self.auto_results\
                      .options(load_only("output", "failure", "skip"))\
                      .all():
            if result.result == 'passed':
                ret['auto_passed'] += 1
            elif result.result == 'failed':
                ret['auto_failed'] += 1
            elif result.result == 'skipped':
                ret['auto_skipped'] += 1

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
        ret['tags'] = [tag.name for tag in self.tags.all()]
        properties = {}
        for prop in self.properties.all():
            properties[prop.name] = prop.value
        ret['properties'] = properties
        if self.submit_date:
            ret['submit_date'] = self.submit_date.isoformat()
        ret['polarion_id'] = self.polarion_id
        if detailed:
            ret.update(self.get_statistics())
        return ret


class AutoResult(db.Model):
    __tablename__ = 'auto_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='auto_results', single_parent=True)

    case = db.Column(db.String(65535), nullable=False, primary_key=True)
    time = db.Column(db.Float(), default=0.0, nullable=False)
    skip = db.Column(db.String(65535), nullable=True)
    failure = db.Column(db.String(65535), nullable=True)
    output = db.Column(db.Text(), nullable=True)
    source = db.Column(db.Text(), nullable=True)
    comment = db.Column(db.String(65535), nullable=True)

    linkage_results = db.relationship("LinkageResult", back_populates="auto_result", viewonly=True, cascade="all, delete")

    @hybrid_property
    def result(self):
        if self.skip:
            return 'skipped'
        elif self.failure:
            return 'failed'
        elif self.output:
            return 'passed'
        elif all(text == "black-listed" for text in [self.skip, self.failure, self.output]):
            return "black-listed"
        elif all(text is None for text in [self.skip, self.failure, self.output]):
            return "missing"
        return None

    def __repr__(self):
        return '<TestResult %s-%s>' % (self.run_id, self.case)

    def __init__(self, **result):
        for key, value in result.items():
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

    def gen_linkage_result(self, session=None):
        """
        Take a AutoResult instance, rewrite it's error and linkage_result
        with data in caselink.
        """
        if not session:
            session = db.session

        try:
            this_autocase = CaseLink.AutoCase(self.case).refresh()
        except (HTTPError, ConnectionError) as err:
            return

        _linkage_result = self.result
        _linkage_error = None

        if _linkage_result == "black-listed":
            _linkage_result = "ignored"
            _linkage_error = "black-listed"

        if _linkage_result == "failed":
            # Auto Case failed with message <self['failure']>
            _linkage_result = None
            _linkage_error = 'UnknownIssue'

            for failure in this_autocase.failures:
                if re.match(failure.failure_regex, self.failure) is not None:
                    _linkage_result = "failed"
                    _linkage_error = 'KnownIssue'

        elif _linkage_result == "missing":
            _linkage_result = None
            _linkage_error = "Missing"

        manualcases = [case.id for case in this_autocase.manualcases]
        for manualcase_id in manualcases:
            manualcase, _ = get_or_create(session, ManualResult,
                                          run_id=self.run_id, case=manualcase_id)
            if _:
                manualcase.gen_linkage_result(session)
            linkage_result, _ = get_or_create(session, LinkageResult,
                                              run_id=self.run_id,
                                              manual_result_id=manualcase.case,
                                              auto_result_id=self.case)
            linkage_result.result = _linkage_result
            linkage_result.error = _linkage_error

            session.add(linkage_result)
            session.commit()

            manualcase.refresh_result()
            manualcase.refresh_comment()
            manualcase.refresh_duration()


class ManualResult(db.Model):
    """
    Presents a workitem result on polarion.
    """
    __tablename__ = 'manual_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='manual_results', single_parent=True)

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), default=0.0, nullable=False)
    comment = db.Column(db.String(65535), nullable=True)

    result = db.Column(db.String(255), nullable=True)
    linkage_results = db.relationship("LinkageResult", back_populates="manual_result", viewonly=True, cascade="all, delete")

    @validates('result')
    def validate_result(self, key, result):
        assert result in ['passed', 'failed', 'incomplete', ]
        return result

    def __repr__(self):
        return '<ManualCaseResult %s-%s: %s>' % (self.run_id, self.case, self.result)

    def __init__(self, **result):
        for key, value in result.items():
            setattr(self, key, value)

    def as_dict(self, detailed=False):
        ret = {}
        for c in self.__table__.columns:
            ret[c.name] = getattr(self, c.name)
        return ret

    def gen_linkage_result(self, session=None):
        session = session or db.session
        this_workitem = CaseLink.ManualCase(self.case)
        for this_autocase in this_workitem.autocases:
            auto_result, _ = get_or_create(session, AutoResult,
                                           run_id=self.run_id,
                                           case=this_autocase.id)
            if _:
                linkage_result, _ = get_or_create(session, LinkageResult,
                                                  run_id=self.run_id,
                                                  manual_result_id=self.case,
                                                  auto_result_id=this_autocase.id)
                linkage_result.result = None
                linkage_result.error = "Missing"

    def refresh_result(self, linkage_results=None):
        """
        For a manual case:
            * If all linkage result is passed, or at least one's result is passed and
              other's result is ignored, manual case will be marked passed.
            * If all linkage result is skipped, or at lease one's result is skipped and
              other's result is ignored or None, manual case will be marked ignored.
            * If all linkage result is ignored, manual case makred ignored
            * If any linkage result is failed, manual case marked failed
            * Otherwise, manual case marked incomplete (blocked)
        """
        linkage_results = self.linkage_results
        if any(r.result == "missing" for r in linkage_results):
            self.result = "incomplete"

        elif any(r.result == "failed" for r in linkage_results):
            self.result = "failed"

        elif all(r.result == "ignored" or r.result == "passed" for r in linkage_results):
            if any(r.result == "passed" for r in linkage_results):
                self.result = "passed"

        elif all(r.result == "ignored" or r.result == "skipped" for r in linkage_results):
            if any(result == "skipped" for result in linkage_results):
                self.result = "skipped"

        elif all(r.result == "ignored" for r in linkage_results):
            self.result = "ignored"

        else:
            self.result = "incomplete"

    def refresh_comment(self, linkage_results=None):
        comments = []
        for result in self.linkage_results:
            _result = result.result
            _error = result.error or "No error"
            if result.result:
                comments.append("%s case with %s: \"%s\"" %
                                (_result.title(), _error, result.auto_result_id))
            else:
                comments.append("Blocking case with Error %s: %s" % (_error, result.auto_result_id))
            comments.sort()
        self.comment = "\n".join(comments)

    def refresh_duration(self, linkage_results=None):
        self.time = 0
        for result in self.linkage_results:
            _auto_case = result.auto_result
            self.time += float(_auto_case.time)


class LinkageResult(db.Model):
    """
    Presend a reason why a manual case is marked passed/failed/incomplete
    """
    __tablename__ = 'linkage_results'
    __table_args__ = (
        ForeignKeyConstraint(["run_id", "manual_result_id"],
                             [ManualResult.run_id, ManualResult.case]),
        ForeignKeyConstraint(["run_id", "auto_result_id"],
                             [AutoResult.run_id, AutoResult.case]),
        {})

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    manual_result_id = db.Column(db.String(255), primary_key=True, nullable=False)
    auto_result_id = db.Column(db.String(65535), primary_key=True, nullable=False)

    run = db.relationship('Run', back_populates='linkage_results', single_parent=True, viewonly=True)
    manual_result = db.relationship('ManualResult', back_populates='linkage_results',
                                    single_parent=True, viewonly=True)
    auto_result = db.relationship('AutoResult', back_populates='linkage_results',
                                  single_parent=True, viewonly=True)

    error = db.Column(db.String(255), nullable=True)
    result = db.Column(db.String(255), nullable=True)

    @validates('error')
    def validate_error(self, key, error):
        """
        Validate if error is legal:

        Valid errors:
            'UnknownIssue': Auto case failed for unknown reason.
            'Missing': Auto case not ran.
            None: No error, result must be avaliable.
        """
        assert error in ['UnknownIssue', 'Missing', None, ]
        return error

    @validates('result')
    def validate_linkage_result(self, key, result):
        """
        Validate if result is legal:
        """
        assert result in ['skipped', 'passed', 'failed', 'ignored', None, ]
        return result

    def __repr__(self):
        return ' %s, Description:(%s)>' % (self.name, self.desc)

    def __init__(self, **result):
        for key, value in result.items():
            setattr(self, key, value)
