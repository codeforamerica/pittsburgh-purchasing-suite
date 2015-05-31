# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''

import time
import urllib2
import json

from flask import (
    Blueprint, render_template, jsonify, current_app
)
from purchasing.extensions import login_manager
from purchasing.users.models import User
from purchasing.public.models import AppStatus

blueprint = Blueprint('public', __name__, static_folder="../static")

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

@blueprint.route("/", methods=["GET", "POST"])
def home():
    return render_template("public/home.html")

@blueprint.route("/about/")
def about():
    return render_template("public/about.html")

@blueprint.route('/_status')
def status():
    response = {
        'status': 'ok',
        'dependencies': ['Sendgrid', 'Postgres'],
        'resources': {}
    }

    try:
        status = AppStatus.query.first()
        if status.status != 'ok':
            response['status'] = status.status
    except Exception, e:
        response['status'] = 'Database is unavailable: {}'.format(e)

    try:
        url = 'https://sendgrid.com/api/stats.get.json?api_user={user}&api_key={_pass}&days=30'.format(
            user=current_app.config['MAIL_USERNAME'],
            _pass=current_app.config['MAIL_PASSWORD']
        )

        sendgrid = json.loads(urllib2.urlopen(url).read())
        sent = sum([m['delivered'] + m['repeat_bounces'] for m in sendgrid])
        response['resources']['Sendgrid'] = '{}% used'.format((100 * float(sent)) / int(
            current_app.config.get('SENDGRID_MONTHLY_LIMIT', 40000)
        ))

    except Exception, e:
        response['status'] = 'Sendgrid is unavailable: {}'.format(e)

    response['updated'] = int(time.time())
    return jsonify(response)
