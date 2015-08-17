# -*- coding: utf-8 -*-
'''The app module, containing the app factory function.'''

import logging
import os
import types
import sys
import datetime

from pkgutil import iter_modules
from importlib import import_module

from flask import Flask, render_template, Blueprint
from flask_login import current_user

from purchasing.settings import ProdConfig
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

def create_app(config_object=ProdConfig):
    '''An application factory, as explained here:
        http://flask.pocoo.org/docs/patterns/appfactories/

    :param config_object: The configuration object to use.
    '''
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_jinja_extensions(app)
    register_errorhandlers(app)

    make_celery(app)

    @app.before_first_request
    def before_first_request():
        if app.debug and not app.testing:
            # log to console for dev
            app.logger.setLevel(logging.DEBUG)

        elif app.testing:
            # disable logging output
            app.logger.setLevel(logging.CRITICAL)

        else:
            # for heroku, just send everything to the console (instead of a file)
            # and it will forward automatically to the logging service

            class UserEmailFilter(logging.Filter):
                '''
                This is a filter which injects contextual information into the log.
                '''
                def filter(self, record):
                    user_id = current_user.email if not current_user.is_anonymous() else 'anonymous'
                    record.user_id = user_id
                    return True

            _filter = UserEmailFilter()

            stdout = logging.StreamHandler(sys.stdout)
            stdout.setFormatter(logging.Formatter(
                '%(asctime)s | %(name)s | %(user_id)s | %(funcName)s | %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s'
            ))
            app.logger.addFilter(_filter)
            app.logger.addHandler(stdout)
            app.logger.setLevel(logging.DEBUG)

            # log to a file. this is commented out for heroku deploy, but kept
            # in case we need it later

            # file_handler = logging.handlers.RotatingFileHandler(log_file(app), 'a', 10000000, 10)
            # file_handler.setFormatter(logging.Formatter(
            #     '%(asctime)s | %(name)s | %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s')
            # )
            # app.logger.addHandler(file_handler)
            # app.logger.setLevel(logging.DEBUG)

        app.logger.info("app config before_first_request: %s", app.config)

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
