# -*- coding: utf-8 -*-

from flask import Blueprint

blueprint = Blueprint(
    'wexplorer', __name__, url_prefix='/scout',
    template_folder='../templates'
)

from . import views
