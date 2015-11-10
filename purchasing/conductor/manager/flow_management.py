# -*- coding: utf-8 -*-

from flask import render_template, redirect, url_for, flash, abort

from purchasing.decorators import requires_roles
from purchasing.data.stages import Stage
from purchasing.data.flows import Flow
from purchasing.conductor.forms import FlowForm, NewFlowForm

from purchasing.conductor.manager import blueprint

@blueprint.route('/flow/new', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def new_flow():
    '''Create a new flow

    :status 200: Render the new flow template
    :status 302: Try to create a new flow using the
        :py:class:`~purchasing.conductor.forms.NewFlowForm`, redirect
        to the flows list view if successful
    '''
    stages = Stage.choices_factory()
    form = NewFlowForm(stages=stages)
    if form.validate_on_submit():
        stage_order = []
        for entry in form.stage_order.entries:
            # try to evaluate the return value as an ID
            try:
                stage_id = int(entry.data)
            # otherwise it's a new stage
            except ValueError:
                new_stage = Stage.create(name=entry.data)
                stage_id = new_stage.id
            stage_order.append(stage_id)

        Flow.create(flow_name=form.flow_name.data, stage_order=stage_order)
        flash('Flow created successfully!', 'alert-success')
        return redirect(url_for('conductor.flows_list'))

    return render_template('conductor/flows/new.html', stages=stages, form=form)

@blueprint.route('/flows')
@requires_roles('conductor', 'admin', 'superadmin')
def flows_list():
    '''List all flows

    :status 200: Render the all flows list template
    '''
    flows = Flow.query.order_by(Flow.flow_name).all()
    active, archived = [], []
    for flow in flows:
        if flow.is_archived:
            archived.append(flow)
        else:
            active.append(flow)
    return render_template('conductor/flows/browse.html', active=active, archived=archived)

@blueprint.route('/flow/<int:flow_id>', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def flow_detail(flow_id):
    '''View/edit a flow's details

    :status 200: Render the flow edit template
    :status 302: Post changes to the a flow  using the submitted
        :py:class:`~purchasing.conductor.forms.FlowForm`, redirect back to
        the current flow's detail page if successful
    '''
    flow = Flow.query.get(flow_id)
    if flow:
        form = FlowForm(obj=flow)
        if form.validate_on_submit():
            flow.update(
                flow_name=form.data['flow_name'],
                is_archived=form.data['is_archived']
            )

            flash('Flow successfully updated', 'alert-success')
            return redirect(url_for('conductor.flow_detail', flow_id=flow.id))

        return render_template('conductor/flows/edit.html', form=form, flow=flow)
    abort(404)
