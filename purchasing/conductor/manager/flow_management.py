# -*- coding: utf-8 -*-

from flask import render_template, redirect, url_for

from purchasing.decorators import requires_roles
from purchasing.data.stages import Stage
from purchasing.conductor.forms import FlowForm

from purchasing.conductor.manager import blueprint

@blueprint.route('/flow/new', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def new_flow():
    stages = Stage.choices_factory()
    form = FlowForm(stages=stages)
    if form.validate_on_submit():
        return redirect(url_for('conductor.new_flow'))
    return render_template('conductor/flows.html', stages=stages, form=form)
