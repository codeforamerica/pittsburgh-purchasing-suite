#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import os
from flask import current_app
from flask_script import Manager, Shell, Server, prompt_bool
from flask_migrate import MigrateCommand
from flask.ext.assets import ManageAssets

from purchasing.app import create_app
from purchasing.settings import DevConfig, ProdConfig
from purchasing.database import db

from purchasing.public.models import AppStatus

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
@manager.option('-d', '--department', dest='dept', default='Other')
def seed_user(email, role, dept):
    '''
    Creates a new user in the database.
    '''
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
                role_id=role,
                department=dept
            )
            db.session.add(new_user)
            db.session.commit()
            print 'User {email} successfully created!'.format(email=seed_email)
        except Exception, e:
            print 'Something went wrong: {exception}'.format(exception=e.message)
    return

@manager.option(
    '-f', '--file', dest='filepath',
    default='./purchasing/data/importer/files/2015-05-22-contractlist.csv'
)
def import_old_contracts(filepath):
    '''
    Takes a csv of old contracts and imports them into the DB
    '''
    from purchasing.data.importer.old_contracts import main
    print 'Importing data from {filepath}\n'.format(filepath=filepath)
    main(filepath)
    print 'Import finished!'
    return

@manager.option('-u', '--user_id', dest='user', default=os.environ.get('AWS_ACCESS_KEY_ID'))
@manager.option('-p', '--secret', dest='secret', default=os.environ.get('AWS_SECRET_ACCESS_KEY'))
@manager.option('-b', '--bucket', dest='bucket', default=os.environ.get('S3_BUCKET_NAME'))
@manager.option(
    '-d', '--directory', dest='directory',
    default='./purchasing/data/importer/files/costars/'
)
def import_costars(user, secret, bucket, directory):
    '''
    Takes a directory which contains a number of csv files with the
    costars data, and then important them into the DB
    '''
    from purchasing.data.importer.costars import main
    for file in os.listdir(directory):
        if file.endswith('.csv'):
            print 'Importing data from {file}'.format(file=file)
            main(os.path.join(directory, file), file, user, secret, bucket)
    print 'Import finished!'
    return

@manager.option(
    '-f', '--file', dest='filepath',
    default='./purchasing/data/importer/files/2015-05-28-nigp-cleaned.csv'
)
def import_nigp(filepath):
    from purchasing.data.importer.nigp import main
    print 'Importing data from {filepath}\n'.format(filepath=filepath)
    main(filepath)
    print 'Import finished!'
    return

@manager.option('-a', '--all', dest='_all', default=None)
def scrape(_all):
    from purchasing.data.importer.scrape_county import main
    print 'Scraping County'
    main(_all)
    print 'Scraping Finished'
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

@manager.option('-u', '--user_id', dest='user')
@manager.option('-p', '--secret', dest='secret')
@manager.option('-b', '--bucket', dest='bucket')
def upload_assets(user, secret, bucket):
    access_key = user if user else app.config['AWS_ACCESS_KEY_ID']
    access_secret = secret if secret else app.config['AWS_SECRET_ACCESS_KEY']
    bucket = bucket if bucket else app.config['S3_BUCKET_NAME']

    import subprocess
    # build assets and capture the output
    print 'Building assets...'
    proc = subprocess.Popen(
        ['python', 'manage.py', 'assets', 'build'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    proc.wait()

    print 'Connecting to S3...'
    from boto.s3.connection import S3Connection
    conn = S3Connection(
        aws_access_key_id=access_key,
        aws_secret_access_key=access_secret
    )
    bucket = conn.get_bucket(bucket)

    print 'Uploading files...'
    for path in proc.communicate()[0].split('\n')[:-1]:
        key = path.split('public')[1]
        file = current_app.config['APP_DIR'] + '/static' + key
        print 'Uploading {}'.format(key)
        _file = bucket.new_key('/static' + key)
        _file.set_contents_from_filename(file)
        _file.set_acl('public-read')

    print 'Uploading images...'
    for root, _, files in os.walk(current_app.config['APP_DIR'] + '/static/img'):
        for file in files:
            print 'Uploading {}'.format(file)
            _file = bucket.new_key('/static/img/' + file)
            _file.set_contents_from_filename(os.path.join(root, file))
            _file.set_acl('public-read')
    return

@manager.command
def all_clear():
    status = AppStatus.query.first()
    status.status = 'ok'
    status.last_updated = datetime.datetime.now()
    status.message = None
    db.session.commit()
    print 'All clear!'
    return

manager.add_command('server', Server(port=os.environ.get('PORT', 9000)))
manager.add_command('shell', Shell(make_context=_make_context))
manager.add_command('db', MigrateCommand)
manager.add_command('assets', ManageAssets)

if __name__ == '__main__':
    manager.run()
