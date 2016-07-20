from app import db
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

class Run(db.Model):
    __tablename__ = 'run'
    __table_args__ = {'sqlite_autoincrement': True,}
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

    conflict_id = db.Column(db.Integer, db.ForeignKey('conflict.id'), nullable=True)
    conflict = db.relationship('Conflict', back_populates='results')

    case = db.Column(db.String(255), nullable=False, primary_key=True)
    time = db.Column(db.Float(), nullable=False)
    failure = db.Column(db.String(65535), nullable=True)
    skip = db.Column(db.String(65535), nullable=True)
    source = db.Column(db.String(65535), nullable=False)
    manualcases = db.Column(db.String(65535), nullable=True)
    bugs = db.Column(db.String(65535), nullable=True)
    bug = db.Column(db.String(65535), nullable=True)

    def __repr__(self):
        return '<TestResult %s>' % self.name

    def __init__(self, **result):
        for key, value in result.iteritems():
            setattr(self, key, value)

    def as_dict(self, show_conflict=True):
        ret = {}
        for c in self.__table__.columns:
            if c.name != 'date':
                ret[c.name] = getattr(self, c.name)
        if show_conflict and self.conflict:
            ret['conflict'] = {
                'id': self.conflict_id,
                'resolve': self.conflict.resolve
            }
        return ret


class Conflict(db.Model):
    __tablename__ = 'conflict'
    __table_args__ = {'sqlite_autoincrement': True,}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    results = db.relationship('Result', back_populates='conflict', lazy='dynamic')
    resolve = db.Column(db.String(255), nullable=False, default='TODO')

    def __repr__(self):
        return '<Conflict %s>' % self.results

    def __init__(self, **conflict):
        for key, value in conflict.iteritems():
            setattr(self, key, value)

    def as_dict(self):
        ret = {}
        for c in self.__table__.columns:
            if c.name != 'date':
                ret[c.name] = getattr(self, c.name)
        results = ret['results'] = []
        for result in self.results.all():
            results.append(result.as_dict(show_conflict=False))
        return ret
