# -*- coding: utf-8 -*-

import json
import urllib
import urllib2
from flask import (
    Blueprint, render_template, request, flash,
    current_app, abort
)

from purchasing.users.models import User

from flask.ext.login import current_user, login_user, logout_user

blueprint = Blueprint(
    'users', __name__, url_prefix='/users',
    template_folder='../templates'
)

@blueprint.route("/login", methods=["GET"])
def login():
    user = current_user if not current_user.is_anonymous() else dict(email=None)
    return render_template("users/login.html", current_user=user)

@blueprint.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    if request.args.get('persona', None):
        return 'OK'
    else:
        flash('Logged out successfully!', 'alert-success')
        return render_template('users/logout.html')

@blueprint.route('/auth', methods=['POST'])
def auth():
    '''
    Endpoint from AJAX request for authentication from persona
    '''
    data = urllib.urlencode({
        'assertion': request.form.get('assertion'),
        'audience': current_app.config.get('BROWSERID_URL')
    })
    req = urllib2.Request('https://verifier.login.persona.org/verify', data)

    response = json.loads(urllib2.urlopen(req).read())
    if response.get('status') != 'okay':
        abort(403)

    next_url = request.args.get('next', None)
    email = response.get('email')
    user = User.query.filter(User.email == email).first()
    if user:
        login_user(user)
        flash('Logged in successfully!', 'alert-success')
        return next_url if next_url else '/'
    else:
        abort(403)
