# -*- coding: utf-8 -*-

from flask import Blueprint

URL_PREFIX = '/sherpa'

blueprint = Blueprint(
    URL_PREFIX.lstrip('/'), __name__, url_prefix=URL_PREFIX,
    static_folder='../static', template_folder='../templates'
)

from . import routes
