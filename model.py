import re
import caselink as CaseLink
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, load_only, deferred
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

    def as_dict(self, detailed=False):
        ret = {}
        for c in self.__table__.columns:
            if c.name != 'date':
                ret[c.name] = getattr(self, c.name)
        return ret


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
    polarion_id = db.Column(db.String(65535), unique=False, nullable=True)

    auto_results = db.relationship('AutoResult', back_populates='run', lazy='dynamic')
    manual_results = db.relationship('ManualResult', back_populates='run', lazy='dynamic')
    linkage_results = db.relationship("LinkageResult", back_populates="run", cascade="all, delete")

    # Denormalization for faster statistics

    __statistics_cols = [
        'auto_passed', 'auto_failed', 'auto_skipped', 'auto_ignored',
        'auto_missing', 'auto_error', 'auto_nolinkage',
        'manual_passed', 'manual_failed', 'manual_skipped', 'manual_ignored',
        'manual_error',
    ]
    auto_passed = db.Column(db.Integer, nullable=True)
    auto_failed = db.Column(db.Integer, nullable=True)
    auto_skipped = db.Column(db.Integer, nullable=True)
    auto_ignored = db.Column(db.Integer, nullable=True)
    auto_missing = db.Column(db.Integer, nullable=True)
    auto_error = db.Column(db.Integer, nullable=True)
    auto_nolinkage = db.Column(db.Integer, nullable=True)
    manual_passed = db.Column(db.Integer, nullable=True)
    manual_failed = db.Column(db.Integer, nullable=True)
    manual_skipped = db.Column(db.Integer, nullable=True)
    manual_ignored = db.Column(db.Integer, nullable=True)
    manual_error = db.Column(db.Integer, nullable=True)

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

    def gen_statistics(self):
        for col in self.__statistics_cols:
            setattr(self, col, 0)

        for result in self.auto_results\
                      .options(load_only("result", "comment"))\
                      .all():
            if result.result == 'passed':
                self.auto_passed = (self.auto_passed or 0) + 1
            elif result.result == 'failed':
                self.auto_failed = (self.auto_failed or 0) + 1
                if "UnknownIssue" in result.comment:
                    self.auto_error = (self.auto_error or 0) + 1
            elif result.result == 'skipped':
                self.auto_skipped = (self.auto_skipped or 0) + 1
            elif result.result == 'missing':
                self.auto_missing = (self.auto_missing or 0) + 1
            elif result.result == 'ignored':
                self.auto_ignored = (self.auto_ignored or 0) + 1
            else:
                self.auto_error = (self.auto_error or 0) + 1
            if result.comment is None:
                self.auto_nolinkage = (self.auto_nolinkage or 0) + 1

        for result in self.manual_results\
                      .options(load_only("result"))\
                      .all():
            if result.result == 'failed':
                self.manual_failed = (self.manual_failed or 0) + 1
            elif result.result == 'passed':
                self.manual_passed = (self.manual_passed or 0) + 1
            elif result.result == 'skipped':
                self.manual_skipped = (self.manual_skipped or 0) + 1
            elif result.result == 'ignored':
                self.manual_ignored = (self.manual_ignored or 0) + 1
            else:
                self.manual_error = (self.manual_error or 0) + 1

    def get_statistics(self):
        ret = {}
        for col in self.__statistics_cols:
            if getattr(self, col) is None:
                self.gen_statistics()
            ret[col] = getattr(self, col)
        return ret

    def blocking_errors(self, exclude=['Missing'], ignore_resulted=True):
        ret = []
        if len(self.linkage_results) == 0:
            return ["No Linkage result avaliable"]
        if exclude == "ALL":
            return []
        for linkage_result in self.linkage_results:
            if ignore_resulted and linkage_result.result:
                continue
            if linkage_result.error and linkage_result.error not in exclude:
                ret.append("Auto case %s is blocking %s with error %s" %
                           (linkage_result.auto_result_id, linkage_result.manual_result_id, linkage_result.error))
        return ret

    def short_unique_name(self):
        return "%s %s" % (self.name, self.id)

    def as_dict(self, statistics=False):
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
        if statistics:
            ret.update(self.get_statistics())
        return ret


class AutoResult(db.Model):
    __tablename__ = 'auto_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='auto_results', single_parent=True)

    case = db.Column(db.String(65535), nullable=False, primary_key=True)
    time = db.Column(db.Float(), default=0.0, nullable=False)
    skip = deferred(db.Column(db.Text(), nullable=True))
    failure = deferred(db.Column(db.Text(), nullable=True))
    output = deferred(db.Column(db.Text(), nullable=True))
    source = deferred(db.Column(db.Text(), nullable=True))
    comment = db.Column(db.Text(), nullable=True)
    result = db.Column(db.String(255), nullable=True)

    linkage_results = db.relationship("LinkageResult", back_populates="auto_result", viewonly=True, cascade="all, delete")

    def __repr__(self):
        return '<TestResult %s-%s>' % (self.run_id, self.case)

    def __init__(self, **result):
        for key, value in result.items():
            setattr(self, key, value)

    @validates('result')
    def validate_result(self, key, result):
        assert result in ['passed', 'failed', 'skipped', 'missing', 'invalid', 'ignored', None]
        return result

    def as_dict(self, detailed=False):
        ret = {}
        for c in self.__table__.columns:
            if c.name not in ['output']:
                ret[c.name] = getattr(self, c.name)
        ret['result'] = self.result
        if not detailed:
            ret['output'] = 'Not showing'
        else:
            ret['output'] = self.output
        return ret

    def refresh_comment(self):
        comments = []
        for result in self.linkage_results:
            _result = result.result
            _error = result.error
            if result.result:
                if result.detail:
                    comments.append("%s: \"%s\" with detail: %s" %
                                    (_result.title(), result.manual_result_id, result.detail))
                else:
                    comments.append("%s: \"%s\"" %
                                    (_result.title(), result.manual_result_id))
            else:
                comments.append("Blocking with %s: %s" % (_error, result.manual_result_id))
        comments.sort()
        self.comment = "\n".join(comments)

    def refresh_result(self):
        if self.skip:
            if "BLACKLISTED" in self.skip:
                self.result = 'ignored'
            else:
                self.result = 'skipped'
        elif self.failure:
            self.result = 'failed'
        elif self.output:
            self.result = 'passed'
        elif all(text is None for text in [self.skip, self.failure, self.output]):
            self.result = 'missing'
        else:
            self.result = 'invalid'

    def _check_failure(self, autocase):
        failures = []
        for failure in autocase.autocase_failures:
            if re.match(failure.failure_regex, self.failure) is not None:
                for bl in failure.blacklist_entries:
                    if bl.json['workitems'] and bl.json['bugs']:
                        failures.append((bl.json['workitems'], 'failed', bl.json['bugs'], bl.status, bl.description))
                    else:
                        failures.append((bl.json['workitems'], 'ignored', bl.json['bugs'], bl.status, bl.description))
        return failures

    def gen_linkage_result(self, session=None, gen_manual=True):
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

        def _gen_linkage_result(workitems, result, error, detail):
            for workitem_id in workitems:
                workitem, _ = get_or_create(session, ManualResult,
                                            run_id=self.run_id, case=workitem_id)
                if _:
                    workitem.gen_linkage_result(session)
                linkage_result, _ = get_or_create(session, LinkageResult,
                                                  run_id=self.run_id,
                                                  manual_result_id=workitem.case,
                                                  auto_result_id=self.case)
                linkage_result.result = _linkage_result
                linkage_result.error = _linkage_error
                linkage_result.detail = _linkage_detail

                workitem.refresh_result()
                workitem.refresh_comment()
                workitem.refresh_duration()

        _linkage_result = self.result
        _linkage_error, _linkage_detail = None, None

        if _linkage_result == "failed":
            known_failures = self._check_failure(this_autocase)
            if not known_failures:
                _linkage_result, _linkage_error = None, "UnknownIssue"
            else:
                for wis, result, bugs, status, desc in known_failures:
                    _linkage_result, _linkage_error = result, None
                    _linkage_detail = ("%s: Workitems %s %s for bugs %s: %s" %
                                       (status, wis, result, bugs, desc))
                    _gen_linkage_result(wis, _linkage_result, _linkage_error, _linkage_detail)

        elif _linkage_result == "black-listed":
            _linkage_result, _linkage_error = "ignored", "black-listed"

        elif _linkage_result == "missing":
            _linkage_result, _linkage_error = None, "Missing"

        elif _linkage_result == "ignored":
            _linkage_result, _linkage_error = None, None

        if gen_manual:
            workitems = [case.id for case in this_autocase.workitems]
        else:
            workitems = [r.manual_result_id for r in self.linkage_results]

        _gen_linkage_result(workitems, _linkage_result, _linkage_error, _linkage_detail)


class ManualResult(db.Model):
    """
    Presents a workitem result on polarion.
    """
    __tablename__ = 'manual_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='manual_results', single_parent=True)

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), default=0.0, nullable=False)
    comment = db.Column(db.Text(), nullable=True)

    result = db.Column(db.String(255), nullable=True)
    linkage_results = db.relationship("LinkageResult", back_populates="manual_result", viewonly=True, cascade="all, delete")

    @validates('result')
    def validate_result(self, key, result):
        assert result in ['passed', 'failed', 'skipped', 'incomplete', None]
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
        this_workitem = CaseLink.WorkItem(self.case)
        for autocase in this_workitem.autocases:
            auto_result, _ = get_or_create(session, AutoResult,
                                           run_id=self.run_id,
                                           case=autocase.id)
            if _:
                auto_result.refresh_result()
                linkage_result, _ = get_or_create(session, LinkageResult,
                                                  run_id=self.run_id,
                                                  manual_result_id=self.case,
                                                  auto_result_id=autocase.id)
                linkage_result.result = None
                linkage_result.error = "Missing"
                auto_result.refresh_comment()

    def refresh_result(self, linkage_results=None):
        linkage_results = self.linkage_results

        if any(r.result == "failed" for r in linkage_results):
            self.result = "failed"

        elif any(r.result is None for r in linkage_results):
            self.result = "incomplete"

        elif all(r.result == "ignored" or r.result == "passed" for r in linkage_results):
            if any(r.result == "passed" for r in linkage_results):
                self.result = "passed"
            else:
                self.result = "skipped"

        elif all(r.result == "ignored" or r.result == "skipped" for r in linkage_results):
            self.result = "skipped"

        else:
            self.result = "incomplete"

    def refresh_comment(self, linkage_results=None):
        comments = []
        for result in self.linkage_results:
            _result = result.result
            _error = result.error
            if result.result:
                if result.detail:
                    comments.append("%s: \"%s\" with detail: %s" %
                                    (_result.title(), result.auto_result_id, result.detail))
                else:
                    comments.append("%s: \"%s\"" %
                                    (_result.title(), result.auto_result_id))
            else:
                comments.append("Blocking with %s : %s" % (_error, result.auto_result_id))
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
                             [ManualResult.run_id, ManualResult.case],
                             on_delete="CASCADE"),
        ForeignKeyConstraint(["run_id", "auto_result_id"],
                             [AutoResult.run_id, AutoResult.case],
                             on_delete="CASCADE"),
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
    detail = db.Column(db.Text(), nullable=True)

    @validates('result')
    def validate_linkage_result(self, key, result):
        """
        Validate if result is legal:
        """
        assert result in ['skipped', 'passed', 'failed', 'ignored', None, ]
        return result

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

    def __repr__(self):
        return ' %s, Description:(%s)>' % (self.name, self.desc)

    def __init__(self, **result):
        for key, value in result.items():
            setattr(self, key, value)

    def as_dict(self):
        return {
            "run_id": self.run_id,
            "auto_result": self.auto_result_id,
            "manual_result": self.manual_result_id,
            "error": self.error,
            "result": self.result,
        }
