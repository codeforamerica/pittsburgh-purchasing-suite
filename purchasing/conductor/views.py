# -*- coding: utf-8 -*-

import urllib2

from flask import (
    Blueprint, render_template, flash, redirect,
    url_for, abort, request, jsonify
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from purchasing.decorators import requires_roles
from purchasing.database import db
from purchasing.data.stages import transition_stage
from purchasing.data.flows import create_contract_stages
from purchasing.data.models import (
    ContractBase, ContractProperty, ContractStage, Stage,
    ContractStageActionItem, ContractNote
)
from purchasing.users.models import User, Role
from purchasing.wexplorer.forms import NoteForm
from purchasing.conductor.forms import EditContractForm

blueprint = Blueprint(
    'conductor', __name__, url_prefix='/conductor',
    template_folder='../templates'
)

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    contracts = db.session.query(
        ContractBase.id, ContractBase.description,
        ContractBase.financial_id, ContractBase.expiration_date,
        ContractBase.current_stage, Stage.name.label('stage_name'),
        ContractBase.updated_at, User.email.label('assigned'),
        ContractProperty.value.label('spec_number'),
        ContractBase.contract_href
    ).join(ContractProperty).outerjoin(Stage).outerjoin(User).filter(
        db.func.lower(ContractBase.contract_type) == 'county',
        ContractBase.expiration_date is not None,
        db.func.lower(ContractProperty.key) == 'spec number',
        ContractBase.id.in_([541, 548])
    ).order_by(ContractBase.expiration_date).all()

    conductors = User.query.join(Role).filter(
        Role.name == 'conductor'
    ).all()

    user_starred = [] if current_user.is_anonymous() else current_user.get_starred()

    return render_template(
        'conductor/index.html',
        contracts=contracts,
        user_starred=user_starred,
        current_user=current_user,
        conductors=[current_user] + conductors
    )

@blueprint.route('/contract/<int:contract_id>', methods=['GET', 'POST'])
@blueprint.route('/contract/<int:contract_id>/stage/<int:stage_id>', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def detail(contract_id, stage_id=-1):
    '''View to control an individual stage update process
    '''
    if request.args.get('transition'):
        clicked = None

        # if request.json.get('current') != 'true':
        #     clicked = int(request.json.get('clicked'))

        stage, mod_contract, complete = transition_stage(contract_id, destination=clicked)
        if complete:
            return redirect(url_for('conductor.edit', contract_id=mod_contract.id))

        return redirect(url_for(
            'conductor.detail', contract_id=contract_id, stage_id=stage_id
        ))

    stages = db.session.query(
        ContractStage.contract_id, ContractStage.id,
        ContractStage.entered, ContractStage.exited, Stage.name,
    ).join(Stage, Stage.id == ContractStage.stage_id).filter(
        ContractStage.contract_id == contract_id
    ).order_by(ContractStage.id).all()

    notes = ContractNote.query.filter(
        ContractNote.contract_id == contract_id
    ).all()

    actions = ContractStageActionItem.query.filter(
        ContractStageActionItem.contract_stage_id == stage_id
    ).all()

    if len(stages) > 0:
        return render_template(
            'conductor/detail.html',
            stages=stages, actions=actions,
            notes=notes, note_form=NoteForm(),
            contract_id=contract_id, current_user=current_user
        )
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit(contract_id):
    '''Update information about a contract
    '''
    contract = ContractBase.query.get(contract_id)

    if contract:
        spec_number = contract.get_spec_number()
        form = EditContractForm(obj=contract)
        form.spec_number.data = spec_number.value

        if form.validate_on_submit():
            data = form.data
            new_spec = data.pop('spec_number', None)

            if new_spec:
                spec_number.value = new_spec

            contract.update(**data)
            flash('Contract Successfully Updated!', 'alert-success')

            return redirect(url_for('conductor.edit', contract_id=contract.id))

        return render_template('conductor/edit.html', form=form, contract=contract)
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit/url-exists', methods=['POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def url_exists(contract_id):
    '''Check to see if a url returns an actual page
    '''
    url = request.json.get('url', '')
    if url == '':
        return jsonify({'status': 404})

    req = urllib2.Request(url)
    request.get_method = lambda: 'HEAD'

    try:
        response = urllib2.urlopen(req)
        return jsonify({'status': response.getcode()})
    except urllib2.HTTPError, e:
        return jsonify({'status': e.getcode()})

@blueprint.route('/contract/<int:contract_id>/assign/<int:user_id>/flow/<int:flow_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def assign(contract_id, flow_id, user_id):
    '''Assign a contract to an admin or a conductor
    '''
    try:
        stages = create_contract_stages(flow_id, contract_id)
        _, contract = transition_stage(contract_id, stages=stages)
    except IntegrityError, e:
        # we already have the sequence for this, so just
        # rollback and pass
        db.session.rollback()
        contract = ContractBase.query.get(contract_id)
    except Exception, e:
        flash('Something went wrong! {}'.format(e.message), 'alert-danger')
        abort(403)

    user = User.query.get(user_id)

    contract.assigned_to = user_id
    db.session.commit()
    flash('Successfully assigned to {}!'.format(user.email), 'alert-success')
    return redirect(url_for('conductor.index'))
