# -*- coding: utf-8 -*-

from flask import Blueprint

blueprint = Blueprint(
    'users', __name__, url_prefix='/users',
    template_folder='../templates'
)

from . import views
