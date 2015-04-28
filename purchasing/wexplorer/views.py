# -*- coding: utf-8 -*-

from flask import Blueprint, render_template

blueprint = Blueprint(
    'wexplorer', __name__, url_prefix='/wexplorer',
    template_folder='../templates'
)

@blueprint.route('/', methods=['GET'])
def explore():
    return render_template(
        'wexplorer/explore.html'
    )
