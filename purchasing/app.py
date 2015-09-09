# -*- coding: utf-8 -*-
'''The app module, containing the app factory function.'''

import sys
import logging
import os
import datetime

from pkgutil import iter_modules
from importlib import import_module

from werkzeug.utils import import_string

from flask import Flask, render_template, Blueprint
from celery import Celery

from flask_login import current_user

from purchasing.assets import assets, test_assets
from purchasing.extensions import (
    bcrypt, cache, db, login_manager,
    migrate, debug_toolbar, admin, s3, mail
)
from purchasing.users.models import AnonymousUser
from purchasing.filters import (
    url_for_other_page, thispage, format_currency, better_title,
    days_from_today, datetimeformat, format_days_from_today
)

# import models so that flask-migrate can auto-detect
from purchasing.public.models import AppStatus

def log_file(app):
    log_dir = '/var/log/chime'
    if not os.access(log_dir, os.W_OK | os.X_OK):
        log_dir = app.config.get('LOG_PATH', app.config['PROJECT_ROOT'] + '/log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return os.path.join(os.path.realpath(log_dir), 'app.log')

def make_celery():
    config = os.environ['CONFIG']
    if isinstance(config, basestring):
        config = import_string(config)
    return Celery(__name__, broker=getattr(config, 'CELERY_BROKER_URL', 'sqla+postgresql://localhost/purchasing'))

celery = make_celery()

def create_app():
    '''An application factory, as explained here:
        http://flask.pocoo.org/docs/patterns/appfactories/

    :param config: A config object or import path to the config object string.
    '''
    config_string = os.environ['CONFIG']
    if isinstance(config_string, basestring):
        config = import_string(config_string)
    else:
        config = config_string
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    register_jinja_extensions(app)
    register_errorhandlers(app)

    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    @app.before_first_request
    def before_first_request():
        register_logging(app, config_string)

    return app

def register_extensions(app):
    test_assets.init_app(app) if app.config.get('TESTING') else assets.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.anonymous_user = AnonymousUser
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    s3.init_app(app)
    mail.init_app(app)

    from flask_sslify import SSLify
    # only trigger SSLify if the app is running on Heroku
    if 'DYNO' in os.environ:
        SSLify(app)
    return None

def register_blueprints(app, package_name='purchasing', package_path=None):
    from purchasing.admin import views
    package_path = package_path if package_path else app.config['APP_DIR']
    rv = []
    for _, name, _ in iter_modules([package_path]):
        m_name = '{}.{}'.format(package_name, name)
        m = import_module(m_name)
        for item in dir(m):
            item = getattr(m, item)
            if isinstance(item, Blueprint):
                app.register_blueprint(item)
            rv.append(item)

    return rv

def register_jinja_extensions(app):
    app.jinja_env.globals['url_for_other_page'] = url_for_other_page
    app.jinja_env.globals['thispage'] = thispage
    app.jinja_env.globals['_current_user'] = current_user
    app.jinja_env.globals['today'] = datetime.date.today()
    app.jinja_env.globals['days_from_today'] = days_from_today
    app.jinja_env.globals['format_days_from_today'] = format_days_from_today
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['title'] = better_title
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    return None

def register_errorhandlers(app):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)

        if error_code == 500:
            app_status = AppStatus.query.first()
            app_status.status = 'error'
            app_status.last_updated = datetime.datetime.now()
            app_status.message = str(error)
            db.session.commit()

        app.logger.exception(error)

        return render_template("errors/{0}.html".format(error_code)), error_code
    for errcode in [401, 403, 404, 413, 500]:
        # for 500-level status codes, change the db status
        app.errorhandler(errcode)(render_error)
    return None

def register_logging(app, config_string):
    if 'prod' in config_string.lower():

        # for heroku, just send everything to the console (instead of a file)
        # and it will forward automatically to the logging service

        # disable the existing flask handler, we are replacing it with our own
        app.logger.removeHandler(app.logger.handlers[0])

        class UserEmailFilter(logging.Filter):
            '''
            This is a filter which injects contextual information into the log.
            '''
            def filter(self, record):
                user_id = current_user.email if not current_user.is_anonymous() else 'anonymous'
                record.user_id = user_id
                return True

        _filter = UserEmailFilter()

        app.logger.setLevel(logging.DEBUG)
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(logging.Formatter(
            '''--------------------------------------------------------------------------------
%(asctime)s | %(levelname)s in %(module)s [%(funcName)s]
%(user_id)s | [%(pathname)s:%(lineno)d]
%(message)s
--------------------------------------------------------------------------------'''
        ))
        app.logger.addFilter(_filter)
        app.logger.addHandler(stdout)

        # log to a file. this is commented out for heroku deploy, but kept
        # in case we need it later

        # file_handler = logging.handlers.RotatingFileHandler(log_file(app), 'a', 10000000, 10)
        # file_handler.setFormatter(logging.Formatter(
        #     '%(asctime)s | %(name)s | %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s')
        # )
        # app.logger.addHandler(file_handler)
        # app.logger.setLevel(logging.DEBUG)

    elif 'test' in config_string.lower():
        app.logger.setLevel(logging.CRITICAL)

    else:
        # log to console for dev
        app.logger.setLevel(logging.DEBUG)

    return None
