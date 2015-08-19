# -*- coding: utf-8 -*-

from flask import Blueprint

blueprint = Blueprint(
    'opportunities_admin', __name__, url_prefix='/beacon/admin',
    static_folder='../static', template_folder='../templates'
)

from . import views
