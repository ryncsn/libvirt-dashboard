#!/usr/bin/env python
# Load Flask and config
from flask import Flask
app = Flask(__name__)
app.config.from_object("config.ActiveConfig")

# Load ORM
from model import db
db.init_app(app)

# Celery task entry
from celery import Celery
def make_celery(app):
    celery = Celery(app.import_name,
                    broker=app.config['CELERY_BROKER'],
                    backend=app.config['CELERY_RESULT_BACKEND'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery
celery = make_celery(app)

# Load utils
from caselink import CASELINK_URL
app.config.update({"CASELINK_URL": CASELINK_URL})

# Load Views
from views.api import restful_api
from views.table import table
from views.dashboard import dashboard
from views.statistics import dashboard_statistics
from views.dt_api import dt_api
app.register_blueprint(dashboard)
app.register_blueprint(table, url_prefix="/table")
app.register_blueprint(restful_api, url_prefix="/api")
app.register_blueprint(dt_api, url_prefix="/dt")
app.register_blueprint(dashboard_statistics, url_prefix="/statistics")

def initdb():
    "Initialize the database"
    with app.app_context():
        db.create_all()

# Load Migration
from flask_migrate import Migrate
migrate = Migrate(app, db)
