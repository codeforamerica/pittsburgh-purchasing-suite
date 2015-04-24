# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''
from flask import (
    Blueprint, render_template
)
from purchasing.extensions import login_manager
from purchasing.user.models import User

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
