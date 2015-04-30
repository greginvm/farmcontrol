#!/usr/bin/env python

import os
import sys

from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand
from gevent import monkey
from flask.ext.assets import ManageAssets

from app import create_app, db, socketio
from app.models import Sensor, SensorType, Device, Contact, Notification, Relay, User

monkey.patch_all()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, Sensor=Sensor, SensorType=SensorType,
                Device=Device, Contact=Contact,
                Notification=Notification, Relay=Relay,
                User=User)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
manager.add_command("assets", ManageAssets())


@manager.command
def dev_data():
    from app.init_db import init

    init(db)


@manager.command
def deploy():
    instance_path = app.instance_path
    print 'using instance_path', instance_path

    if not os.path.isdir(instance_path):
        print 'Instance path does not exist, create:'
        print 'mkdir -p', instance_path
        sys.exit(1)

    install_secret_key()

    from flask.ext.migrate import upgrade

    upgrade()


@manager.command
def create_db():
    print app.config['SQLALCHEMY_DATABASE_URI']
    db.create_all()


def install_secret_key(filename='secret_key'):
    """Configure the SECRET_KEY from a file
    in the instance directory.

    If the file does not exist, print instructions
    to create it from a shell with a random key,
    then exit.

    source: http://flask.pocoo.org/snippets/104/

    """
    print 'Checking secret key'
    filename = os.path.join(app.instance_path, filename)
    try:
        app.config['SECRET_KEY'] = open(filename, 'rb').read()
    except IOError:
        print 'Error: No secret key. Create it with:'
        if not os.path.isdir(os.path.dirname(filename)):
            print 'mkdir -p', os.path.dirname(filename)
        print 'head -c 24 /dev/urandom >', filename
        sys.exit(1)


@manager.command
def runserver():
    install_secret_key()
    app.logger.info('Starting with socketio-gevent')

    from app.dashboard.views import start_routines

    start_routines()
    socketio.run(app)
    app.logger.info('Stopping socketio-gevent')


if __name__ == '__main__':
    manager.run()