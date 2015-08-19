# -*- coding: utf-8 -*-

from flask import render_template

from purchasing.conductor.metrics import blueprint

@blueprint.route('/')
def index():
    return render_template('conductor/metrics/index.html')
