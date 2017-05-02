#!/usr/bin/env python
# Load Flask and config
from flask_migrate import MigrateCommand
from flask_script import Manager
from app import app, db, initdb
# Start the server

manager = Manager(app)
manager.add_command('db', MigrateCommand)

manager.command(initdb)

if __name__ == '__main__':
    manager.run()
