# -*- coding: utf-8 -*-
'''The public module, including the homepage and user auth.'''

from flask import Blueprint

blueprint = Blueprint('public', __name__, static_folder="../static")

from . import views
