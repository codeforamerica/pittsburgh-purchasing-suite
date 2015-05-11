#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import os
from flask_script import Manager, Shell, Server, prompt_bool
from flask_migrate import MigrateCommand

from purchasing.app import create_app
from purchasing.settings import DevConfig, ProdConfig
from purchasing.database import db

if os.environ.get("PITTSBURGH-PURCHASING-SUITE_ENV") == 'prod':
    app = create_app(ProdConfig)
else:
    app = create_app(DevConfig)

HERE = os.path.abspath(os.path.dirname(__file__))
TEST_PATH = os.path.join(HERE, 'tests')

manager = Manager(app)

def _make_context():
    """Return context dict for a shell session so you can access
    app, db, and the User model by default.
    """
    return {'app': app, 'db': db}

@manager.option('-e', '--email', dest='email', default=None)
@manager.option('-r', '--role', dest='role', default=None)
def seed_user(email, role):
    from purchasing.users.models import User
    seed_email = email if email else app.config.get('SEED_EMAIL')
    user_exists = User.query.filter(User.email == seed_email).first()
    if user_exists:
        print 'User {email} already exists'.format(email=seed_email)
    else:
        try:
            new_user = User.create(
                email=seed_email,
                created_at=datetime.datetime.utcnow(),
                role_id=role
            )
            db.session.add(new_user)
            db.session.commit()
            print 'User {email} successfully created!'.format(email=seed_email)
        except Exception, e:
            print 'Something went wrong: {exception}'.format(exception=e.message)
    return

@manager.option(
    '-f', '--file', dest='filepath',
    default='./purchasing/data/importer/files/2015-05-05-contractlist.csv'
)
def import_old_contracts(filepath):
    from purchasing.data.importer.old_contracts import main
    print 'Importing data from {filepath}\n'.format(filepath=filepath)
    main(filepath)
    print 'Import finished!'
    return

@manager.command
def delete_contracts():
    if prompt_bool("Are you sure you want to lose all contracts & companies?"):
        print 'Deleting!'
        from purchasing.data.models import ContractBase, Company
        ContractBase.query.delete()
        Company.query.delete()
        db.session.commit()
    return

manager.add_command('server', Server(port=os.environ.get('PORT', 9000)))
manager.add_command('shell', Shell(make_context=_make_context))
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
