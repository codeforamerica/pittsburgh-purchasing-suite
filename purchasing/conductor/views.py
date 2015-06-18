# -*- coding: utf-8 -*-

import json

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
    ContractBase, ContractProperty, ContractStage, Stage
)
from purchasing.users.models import User, Role

blueprint = Blueprint(
    'conductor', __name__, url_prefix='/conductor',
    template_folder='../templates'
)

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    contracts = db.session.query(
        ContractBase.id, ContractBase.description, ContractBase.financial_id,
        ContractBase.expiration_date, ContractBase.current_stage,
        ContractBase.updated_at, User.email.label('assigned'), ContractProperty.value
    ).join(ContractProperty).outerjoin(Stage).outerjoin(User).filter(
        db.func.lower(ContractBase.contract_type) == 'county',
        ContractBase.expiration_date is not None,
        db.func.lower(ContractProperty.key) == 'spec number',
        ContractBase.id.in_([541, 548])
    ).order_by(ContractBase.expiration_date).all()

    conductors = User.query.join(Role).filter(
        Role.name == 'conductor'
    ).all()

    return render_template(
        'conductor/index.html',
        contracts=contracts,
        current_user=current_user,
        conductors=[current_user] + conductors
    )

@blueprint.route('/<int:contract_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def detail(contract_id):
    stages = db.session.query(
        ContractStage.id, ContractStage.entered,
        ContractStage.exited, Stage.name
    ).join(Stage, Stage.id == ContractStage.stage_id).filter(
        ContractStage.contract_id == contract_id
    ).order_by(ContractStage.id).all()

    if len(stages) > 0:
        return render_template(
            'conductor/detail.html',
            stages=stages,
            contract_id=contract_id,
            current_user=current_user
        )
    abort(404)

@blueprint.route('/<int:contract_id>/transition', methods=['POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def transition(contract_id):
    '''Transition a contract
    '''
    clicked = None

    if request.json.get('current') != 'true':
        clicked = request.json.get('clicked')

    stage, _ = transition_stage(contract_id, destination=clicked)

    return jsonify({
        'stage': stage.as_dict()
    }), 200

@blueprint.route('/<int:contract_id>/assign/<int:user_id>/<int:flow_id>')
@requires_roles('conductor', 'admin', 'superadmin')
def assign(contract_id, flow_id, user_id):

    try:
        stages = create_contract_stages(flow_id, contract_id)
        _, contract = transition_stage(contract_id, stages=stages)
    except IntegrityError, e:
        # we already have the sequence for this, so just
        # rollback and pass
        db.session.rollback()
        pass
    except Exception, e:
        flash('Something went wrong! {}'.format(e.message), 'alert-danger')
        abort(403)

    user = User.query.get(user_id)

    contract.assigned_to = user_id
    db.session.commit()
    flash('Successfully assigned to {}!'.format(user.email), 'alert-success')
    return redirect(url_for('conductor.index'))
