from app import db
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method


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
    results = db.relationship('Result', back_populates='run', lazy='dynamic')
    submitted = db.Column(db.Boolean(), nullable=False, default=False)

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


class Result(db.Model):
    __tablename__ = 'result'

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'), primary_key=True)
    run = db.relationship('Run', back_populates='results')

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), nullable=False)
    failure = db.Column(db.String(65535), nullable=True)
    output = db.Column(db.String(65535), nullable=True)
    source = db.Column(db.String(65535), nullable=False)

    # If bugs is not None, manualcases means cases failed
    # If bugs is None, manualcases means cases passed
    # If error is not None, dashboard faild to look up bug/cases for this autocase
    # Strings splited by '\n'
    skip = db.Column(db.String(65535), nullable=True)
    manualcases = db.Column(db.String(65535), nullable=True)
    bugs = db.Column(db.String(65535), nullable=True)
    error = db.Column(db.String(65535), nullable=True)

    def __repr__(self):
        return '<TestResult %s-%s>' % (self.run_id, self.case)

    def __init__(self, **result):
        for key, value in result.iteritems():
            setattr(self, key, value)

    @hybrid_property
    def status(self):
        if self.error:
            return 'Error'
        if self.skip:
            return 'Skipped with: ' + self.skip
        if self.bugs and self.manualcases:
            return 'Failed ' + ' '.join(self.manualcases.split('\n'))
        if not self.bugs and self.manualcases:
            return 'Passed ' + ' '.join(self.manualcases.split('\n'))
        else:
            return 'Illegal'


    def as_dict(self):
        ret = {}
        for c in self.__table__.columns:
            if c.name != 'date':
                ret[c.name] = getattr(self, c.name)
        ret['status'] = self.status
        return ret
