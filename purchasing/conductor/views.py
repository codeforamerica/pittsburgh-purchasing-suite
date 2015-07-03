# -*- coding: utf-8 -*-

import urllib2
import datetime
import os

from werkzeug import secure_filename

from flask import (
    Blueprint, render_template, flash, redirect,
    url_for, abort, request, jsonify, current_app
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from purchasing.decorators import requires_roles
from purchasing.database import db
from purchasing.notifications import new_contract_autoupdate, send_conductor_alert
from purchasing.data.stages import transition_stage
from purchasing.data.flows import create_contract_stages
from purchasing.data.models import (
    ContractBase, ContractProperty, ContractStage, Stage,
    ContractStageActionItem, Flow
)
from purchasing.data.importer.costars import main as import_costars
from purchasing.users.models import User, Role
from purchasing.conductor.forms import (
    EditContractForm, PostOpportunityForm,
    SendUpdateForm, NoteForm, FileUpload
)

blueprint = Blueprint(
    'conductor', __name__, url_prefix='/conductor',
    template_folder='../templates'
)

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    all_contracts, assigned_contracts = [], []

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
    ).order_by(ContractBase.expiration_date).all()

    conductors = User.query.join(Role).filter(
        Role.name == 'conductor',
        User.email != current_user.email
    ).all()

    user_starred = [] if current_user.is_anonymous() else current_user.get_starred()

    for contract in contracts:
        if contract.assigned:
            assigned_contracts.append(contract)
        else:
            all_contracts.append(contract)

    return render_template(
        'conductor/index.html',
        contracts=all_contracts,
        assigned=assigned_contracts,
        user_starred=user_starred,
        current_user=current_user,
        conductors=[current_user] + conductors,
        path='{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
    )

@blueprint.route('/contract/<int:contract_id>', methods=['GET', 'POST'])
@blueprint.route('/contract/<int:contract_id>/stage/<int:stage_id>', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def detail(contract_id, stage_id=-1):
    '''View to control an individual stage update process
    '''
    if request.args.get('transition'):

        clicked = int(request.args.get('destination')) if \
            request.args.get('destination') else None

        stage, mod_contract, complete = transition_stage(
            contract_id, destination=clicked, user=current_user
        )
        if complete:
            return redirect(url_for('conductor.edit', contract_id=mod_contract.id))

        return redirect(url_for(
            'conductor.detail', contract_id=contract_id, stage_id=stage.id
        ))

    if stage_id == -1:
        # redirect to the current stage page
        contract_stage = ContractStage.query.join(
            ContractBase, ContractBase.id == ContractStage.contract_id
        ).filter(
            ContractStage.contract_id == contract_id,
            ContractStage.stage_id == ContractBase.current_stage_id
        ).first()

        return redirect(url_for(
            'conductor.detail', contract_id=contract_id, stage_id=contract_stage.id
        ))

    stages = db.session.query(
        ContractStage.contract_id, ContractStage.stage_id, ContractStage.id,
        ContractStage.entered, ContractStage.exited, Stage.name,
        Stage.send_notifs, Stage.post_opportunities, ContractBase.description
    ).join(Stage, Stage.id == ContractStage.stage_id).join(
        ContractBase, ContractBase.id == ContractStage.contract_id
    ).filter(
        ContractStage.contract_id == contract_id
    ).order_by(ContractStage.id).all()

    try:
        active_stage = [i for i in stages if i.id == stage_id][0]
        current_stage = [i for i in stages if i.entered and not i.exited][0]
        if active_stage.entered is None:
            abort(404)
    except IndexError:
        abort(404)

    note_form = NoteForm()
    update_form = SendUpdateForm()
    opportunity_form = PostOpportunityForm()

    forms = {
        'activity': note_form, 'update': update_form, 'post': opportunity_form
    }

    active_tab = '#activity'
    submitted_form = request.args.get('form', None)
    if submitted_form:
        if handle_form(forms[submitted_form], submitted_form, stage_id, current_user):
            return redirect(url_for(
                'conductor.detail', contract_id=contract_id, stage_id=stage_id
            ))
        else:
            active_tab = '#' + submitted_form

    actions = ContractStageActionItem.query.filter(
        ContractStageActionItem.contract_stage_id == stage_id
    ).order_by(db.text('taken_at asc')).all()

    actions.extend([
        ContractStageActionItem(action_type='entered', action_detail=active_stage.entered, taken_at=active_stage.entered),
        ContractStageActionItem(action_type='exited', action_detail=active_stage.exited, taken_at=active_stage.exited)
    ])
    actions = sorted(actions, key=lambda stage: stage.get_sort_key())

    if len(stages) > 0:
        return render_template(
            'conductor/detail.html',
            stages=stages, actions=actions, active_tab=active_tab,
            note_form=note_form, update_form=update_form,
            opportunity_form=opportunity_form, contract_id=contract_id,
            current_user=current_user, active_stage=active_stage,
            current_stage=current_stage
        )
    abort(404)

def handle_form(form, form_name, stage_id, user):
    if form.validate_on_submit():
        action = ContractStageActionItem(
            contract_stage_id=stage_id, action_type=form_name,
            taken_by=user.id, taken_at=datetime.datetime.now()
        )
        if form_name == 'activity':
            action.action_detail = {'note': form.data.get('note', '')}

        elif form_name == 'update':
            action.action_detail = {
                'sent_to': form.data.get('send_to', ''),
                'body': form.data.get('body'),
                'subject': form.data.get('subject')
            }
            send_conductor_alert(
                form.data.get('send_to'), form.data.get('subject'),
                form.data.get('body'), current_user.email
            )

        elif form_name == 'opportunity':
            pass

        else:
            return False

        db.session.add(action)
        db.session.commit()
        return True

    return False

@blueprint.route('/contract/<int:contract_id>/stage/<int:stage_id>/note/<int:note_id>/delete', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def delete_note(contract_id, stage_id, note_id):
    try:
        note = ContractStageActionItem.query.get(note_id)
        if note:
            note.delete()
            flash('Note deleted successfully!', 'alert-success')
        else:
            flash("That note doesn't exist!", 'alert-warning')
    except Exception, e:
        flash('Something went wrong: {}'.format(e.message), 'alert-danger')
    return redirect(url_for('conductor.detail', contract_id=contract_id, stage_id=stage_id))

@blueprint.route('/contract/<int:contract_id>/edit', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit(contract_id):
    '''Update information about a contract
    '''
    contract = ContractBase.query.get(contract_id)

    if contract:
        spec_number = contract.get_spec_number()
        form = EditContractForm(obj=contract)

        if form.validate_on_submit():
            data = form.data
            new_spec = data.pop('spec_number', None)

            if new_spec:
                spec_number.key = 'Spec Number'
                spec_number.value = new_spec
                contract.properties.append(spec_number)

            contract.update(**data)
            flash('Contract Successfully Updated!', 'alert-success')
            new_contract_autoupdate(contract, current_user.email)

            return redirect(url_for('conductor.edit', contract_id=contract.id))

        form.spec_number.data = spec_number.value
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
    contract = ContractBase.query.get(contract_id)
    flow = Flow.query.get(flow_id)

    if not flow:
        flash('Something went wrong! That flow doesn\'t exist!', 'alert-danger')
        return redirect('conductor.index')

    try:
        stages = create_contract_stages(flow_id, contract_id, contract=contract)
        _, contract, _ = transition_stage(contract_id, contract=contract, stages=stages)
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

@blueprint.route('/upload_new', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def upload():
    form = FileUpload()
    if form.validate_on_submit():
        _file = request.files.get('upload')
        filename = secure_filename(_file.filename)
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER'), filename)
        _file.save(filepath)
        return render_template('conductor/upload_success.html', filepath=filepath, filename=filename)

    else:
        return render_template('conductor/upload_new.html', form=form)

@blueprint.route('/_process_file', methods=['POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def process_upload():
    filepath = request.form.get('filepath')
    filename = request.form.get('filename')
    try:
        import_costars(filepath, filename, None, None, None)
        return jsonify({'status': 'success'}), 200
    except Exception, e:
        return jsonify({'status': 'error: {}'.format(e)}), 500
