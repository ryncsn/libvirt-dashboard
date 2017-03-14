#!/usr/bin/env python
# Load Flask and config
from flask import Flask, Markup
app = Flask(__name__)
app.config.from_object('config.ActiveConfig')

# Load ORM
from model import db
db.init_app(app)

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

# Load Manager and Migration
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@app.cli.command('initdb')
def init_db_cli():
    init_db()

def init_db():
    with app.app_context():
        db.create_all()

# Start the server
if __name__ == '__main__':
    manager.run()
