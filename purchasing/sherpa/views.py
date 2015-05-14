# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template
)
from purchasing.extensions import login_manager
from purchasing.users.models import User

blueprint = Blueprint(
    'sherpa', __name__, url_prefix='/sherpa',
    static_folder='../static', template_folder='../templates'
)

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

@blueprint.route("/", methods=["GET", "POST"])
def index():
    return render_template("sherpa/index.html")
