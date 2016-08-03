from app import db
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import validates

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
    project = db.Column(db.String(255), nullable=False)
    component = db.Column(db.String(255), nullable=False)
    arch = db.Column(db.String(255), unique=False, nullable=False)
    type = db.Column(db.String(255), unique=False, nullable=False)
    name = db.Column(db.String(255), unique=False, nullable=False)
    date = db.Column(db.DateTime(), unique=False, nullable=False)
    build = db.Column(db.String(255), unique=False, nullable=False)
    version = db.Column(db.String(255), unique=False, nullable=False)
    framework = db.Column(db.String(255), unique=False, nullable=False)
    description = db.Column(db.String(255), unique=False, nullable=True)
    auto_results = db.relationship('AutoResult', back_populates='run', lazy='dynamic')
    manual_results = db.relationship('ManualResult', back_populates='run', lazy='dynamic')
    submit_date = db.Column(db.DateTime(), unique=False, nullable=True)

    @hybrid_property
    def polarion_id(self):
        return "Libvirt-Auto-Record-" + str(self.id)

    def __repr__(self):
        return '<TestRun %s>' % self.name

    def __init__(self, **run):
        for key, value in run.iteritems():
            setattr(self, key, value)

    def as_dict(self):
        ret = {}
        for c in self.__table__.columns:
            if c.name != 'date':
                ret[c.name] = getattr(self, c.name)
        ret['date'] = self.date.isoformat()
        ret['polarion_id'] = self.polarion_id
        return ret


class AutoResult(db.Model):
    __tablename__ = 'auto_result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='auto_results')

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), nullable=False)
    skip = db.Column(db.String(65535), nullable=True)
    failure = db.Column(db.String(65535), nullable=True)
    output = db.Column(db.String(65535), nullable=True)
    source = db.Column(db.String(65535), nullable=True)
    comment = db.Column(db.String(65535), nullable=True)

    # If bugs is not None, manualcases means cases failed
    # If bugs is None, manualcases means cases passed
    # If error is not None, dashboard faild to look up bug/cases for this autocase
    error = db.Column(db.String(255), nullable=True)
    result = db.Column(db.String(255), nullable=True)

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
