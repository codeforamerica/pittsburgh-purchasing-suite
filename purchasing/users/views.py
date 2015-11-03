# -*- coding: utf-8 -*-

import json
import urllib
import urllib2
from flask import (
    render_template, request, flash,
    current_app, abort, url_for, redirect
)

from flask.ext.login import current_user, login_user, logout_user, login_required

from purchasing.database import db
from purchasing.users.forms import DepartmentForm
from purchasing.users.models import User, Role, Department
from purchasing.public.models import AcceptedEmailDomains

from purchasing.users import blueprint

@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    '''View to update user model with data passed through form after validation
    '''
    form = DepartmentForm(obj=current_user)

    if form.validate_on_submit():
        user = current_user
        data = request.form

        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        user.department_id = int(data.get('department'))
        db.session.commit()

        flash('Updated your profile!', 'alert-success')
        data = data.to_dict().pop('csrf_token', None)
        current_app.logger.debug('PROFILE UPDATE: Updated profile for {email} with {data}'.format(
            email=user.email, data=data
        ))

        return redirect(url_for('users.profile'))

    return render_template('users/profile.html', form=form, user=current_user)

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
        current_app.logger.debug('REJECTEDUSER: User login rejected from persona. Messages: {}'.format(response))
        abort(403)

    next_url = request.args.get('next', None)
    email = response.get('email')
    user = User.query.filter(User.email == email).first()

    domain = email.split('@')[1] if len(email.split('@')) > 1 else None

    if user:
        login_user(user)
        flash('Logged in successfully!', 'alert-success')

        current_app.logger.debug('LOGIN: User {} logged in successfully'.format(user.email))
        return next_url if next_url else '/'

    elif AcceptedEmailDomains.valid_domain(domain):
        user = User.create(
            email=email,
            role=Role.query.filter(Role.name == 'staff').first(),
            department=Department.query.filter(Department.name == 'New User').first()
        )
        login_user(user)

        current_app.logger.debug('NEWUSER: New User {} successfully created'.format(user.email))
        return '/users/profile'

    else:
        current_app.logger.debug('NOTINDB: User {} not in DB -- aborting!'.format(email))
        abort(403)
