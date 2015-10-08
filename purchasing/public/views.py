# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''

import time
import datetime
import urllib2
import json

from flask import (
    render_template, jsonify, current_app
)
from purchasing.extensions import login_manager, cache
from purchasing.users.models import User
from purchasing.public.models import AppStatus

from purchasing.public import blueprint

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
        'dependencies': ['Celery', 'Postgres', 'Redis', 'S3', 'Sendgrid'],
        'resources': {}
    }

    # order the try/except blocks in the reverse order of seriousness
    # in terms of an outage
    try:
        url = 'https://sendgrid.com/api/stats.get.json?api_user={user}&api_key={_pass}&days={days}'.format(
            user=current_app.config['MAIL_USERNAME'],
            _pass=current_app.config['MAIL_PASSWORD'],
            days=datetime.date.today().day
        )

        sendgrid = json.loads(urllib2.urlopen(url).read())
        sent = sum([m['delivered'] + m['repeat_bounces'] for m in sendgrid])
        response['resources']['Sendgrid'] = '{}% used'.format((100 * float(sent)) / int(
            current_app.config.get('SENDGRID_MONTHLY_LIMIT', 12000)
        ))

    except Exception, e:
        response['status'] = 'Sendgrid is unavailable: {}'.format(e)

    try:
        # TODO: figure out some way to figure out if s3 is down
        pass
    except Exception, e:
        response['status'] = 'S3 is unavailable: {}'.format(e)

    try:
        redis_up = cache.cache._client.ping()
        if not redis_up:
            response['status'] = 'Redis is down or unavailable'
    except Exception, e:
        response['status'] = 'Redis is down or unavailable'

    try:
        status = AppStatus.query.first()
        if status.status != 'ok':
            if response['status'] != 'ok':
                response['status'] += ' || {}: {}'.format(status.status, status.message)
            else:
                response['status'] = '{}: {}'.format(status.status, status.message)
    except Exception, e:
        response['status'] = 'Database is unavailable: {}'.format(e)

    response['updated'] = int(time.time())
    return jsonify(response)
