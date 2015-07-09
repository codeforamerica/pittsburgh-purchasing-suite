# -*- coding: utf-8 -*-

from flask import Blueprint

blueprint = Blueprint(
    'opportunities', __name__, url_prefix='/beacon',
    static_folder='../static', template_folder='../templates'
)
