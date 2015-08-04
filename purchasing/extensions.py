# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located
in app.py
"""

from purchasing.decorators import ConductorAuthMixin

from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()

from flask_login import LoginManager
login_manager = LoginManager()

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask_migrate import Migrate
migrate = Migrate()

from flask_cache import Cache
cache = Cache()

from flask_debugtoolbar import DebugToolbarExtension
debug_toolbar = DebugToolbarExtension()

from flask_s3 import FlaskS3
s3 = FlaskS3()

from flask_mail import Mail
mail = Mail()

from flask_admin import Admin, AdminIndexView, expose
class PermissionsBase(ConductorAuthMixin, AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')

admin = Admin(endpoint='admin', base_template='admin/purchasing_master.html', index_view=PermissionsBase(), template_mode='bootstrap3')
