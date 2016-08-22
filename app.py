#!/usr/bin/env python
from flask import Flask, request, Markup
from flask import render_template, make_response, jsonify
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_restful import Resource, Api, reqparse, inputs
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from requests import HTTPError

# Load Flask and config
app = Flask(__name__)
app.config.from_object('config.ActiveConfig')

# Load ORM
from model import db
db.init_app(app)

# Load Views
from views.api import restful_api
from views.table import table
from views.dashboard import dashboard
app.register_blueprint(table)
app.register_blueprint(dashboard)
app.register_blueprint(restful_api)

# Load Migration
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

# Extra filter
@app.template_filter('nl2br_simple')
def nl2br_simple(s):
    s = s.replace('\\n', ';')
    return Markup(s)

# Start the server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    manager.run()
