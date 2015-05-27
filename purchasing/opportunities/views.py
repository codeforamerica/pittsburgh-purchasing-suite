# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, url_for
)
from purchasing.extensions import login_manager
from purchasing.users.models import User

blueprint = Blueprint(
    'opportunities', __name__, url_prefix='/opportunities',
    static_folder='../static', template_folder='../templates'
)

@blueprint.route('/')
def index():
    '''
    Landing page for opportunities site
    '''
    return render_template(
        'opportunities/index.html'
    )
