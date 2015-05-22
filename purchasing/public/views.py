# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''
import time

from flask import (
    Blueprint, render_template, jsonify
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
    response = {}
    response['status'] = 'ok'

    try:
        status = AppStatus.query.first()
        if status.status != 'ok':
            response['status'] = status.status
    except:
        response['status'] = 'Database is unavailable'
    response['updated'] = int(time.time())
    response['dependencies'] = []
    response['resources'] = []
    return jsonify(response)
