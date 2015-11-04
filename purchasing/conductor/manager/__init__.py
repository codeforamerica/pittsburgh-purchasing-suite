# -*- coding: utf-8 -*-

from flask import Blueprint

blueprint = Blueprint(
    'conductor', __name__, url_prefix='/conductor',
    template_folder='../templates'
)

from . import index, detail, complete, flow_management
