#!/usr/bin/env python
# Load Flask and config
from flask import Flask
app = Flask(__name__)
app.config.from_object('config.ActiveConfig')

# Load ORM
from model import db
db.init_app(app)

# Load Views
from views.api import restful_api
from views.table import table
from views.dashboard import dashboard
app.register_blueprint(dashboard)
app.register_blueprint(table, url_prefix="/table")
app.register_blueprint(restful_api, url_prefix="/api")

# Load Manager and Migration
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

# Extra filter
@app.template_filter('nl2br_simple')
def nl2br_simple(s):
    s = s.replace('\\n', ';')
    return Markup(s)

def init_db():
    with app.app_context():
        db.create_all()

# Start the server
if __name__ == '__main__':
    init_db()
    manager.run()
