# -*- coding: utf-8 -*-

from flask import Blueprint

blueprint = Blueprint(
    'conductor_metrics', __name__, url_prefix='/conductor/metrics',
    template_folder='../templates'
)

from . import views
