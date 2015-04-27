# -*- coding: utf-8 -*-

from flask import redirect, url_for, flash, request, abort
from flask_login import current_user
from functools import wraps

def requires_roles(*roles):
    '''
    Takes in a list of roles and checks whether the user
    has access to those role
    '''
    def check_roles(view_function):
        @wraps(view_function)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('ERROR! ERROR! ERROR!', 'alert-danger')
                return redirect(request.args.get('next') or '/')
            return view_function(*args, **kwargs)
        return decorated_function
    return check_roles

class AuthMixin(object):
    accepted_roles = ['admin', 'superadmin']

    def is_accessible(self):
        if current_user.is_anonymous():
            return url_for('users.login', next=request.path)
        if current_user.role.name in self.accepted_roles:
            return True

    def _handle_view(self, name, **kwargs):
        if isinstance(self.is_accessible(), str):
            return redirect(self.is_accessible())

class SuperAdminMixin(object):
    def is_accessible(self):
        if current_user.is_anonymous():
            return url_for('users.login', next=request.url)
        if current_user.role.name == 'superadmin':
            return True

    def _handle_view(self, name, **kwargs):
        if isinstance(self.is_accessible(), str):
            return redirect(self.is_accessible())
        if not self.is_accessible():
            return redirect(url_for('admin.index'))
