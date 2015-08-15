# -*- coding: utf-8 -*-

import urllib2
import json

from flask import (
    Blueprint, render_template, flash, redirect,
    url_for, abort, request, jsonify, session
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from purchasing.decorators import requires_roles
from purchasing.database import db
from purchasing.notifications import Notification
from purchasing.data.contracts import clone_a_contract, extend_a_contract
from purchasing.data.stages import transition_stage, get_contract_stages
from purchasing.data.flows import create_contract_stages, switch_flow
from purchasing.data.models import (
    ContractBase, ContractProperty, ContractStage, Stage,
    ContractStageActionItem, Flow
)

from purchasing.users.models import User, Role
from purchasing.conductor.forms import (
    EditContractForm, PostOpportunityForm,
    SendUpdateForm, NoteForm, ContractMetadataForm, CompanyListForm,
    CompanyContactListForm
)

from purchasing.conductor.util import (
    update_contract_with_spec, handle_form, ContractMetadataObj,
    build_action_log, build_subscribers, create_opp_form_obj,
    json_serial, parse_companies
)

from purchasing.opportunities.util import generate_opportunity_form

blueprint = Blueprint(
    'conductor', __name__, url_prefix='/conductor',
    template_folder='../templates'
)

@blueprint.route('/')
@requires_roles('conductor', 'admin', 'superadmin')
def index():
    in_progress = db.session.query(
        db.distinct(ContractBase.id).label('id'),
        ContractBase.description, Flow.flow_name,
        Stage.name.label('stage_name'), ContractStage.entered,
        db.func.string.split_part(User.email, '@', 1).label('assigned'),
    ).join(
        Stage, Stage.id == ContractBase.current_stage_id
    ).join(
        ContractStage, ContractStage.stage_id == ContractBase.current_stage_id
    ).join(
        Flow, Flow.id == ContractBase.flow_id
    ).join(User).filter(
        ContractStage.entered != None,
        ContractBase.assigned_to != None,
        ContractStage.flow_id == ContractBase.flow_id
    ).all()

    all_contracts = db.session.query(
        ContractBase.id, ContractBase.description,
        ContractBase.financial_id, ContractBase.expiration_date,
        ContractProperty.value.label('spec_number'),
        ContractBase.contract_href
    ).outerjoin(ContractProperty).filter(
        db.func.lower(ContractBase.contract_type) == 'county',
        db.func.lower(ContractProperty.key) == 'spec number',
        ContractBase.child == None
    ).order_by(ContractBase.expiration_date).all()

    conductors = User.query.join(Role).filter(
        Role.name == 'conductor',
        User.email != current_user.email
    ).all()

    return render_template(
        'conductor/index.html',
        in_progress=in_progress, _all=all_contracts,
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

        try:
            stage, mod_contract, complete = transition_stage(
                contract_id, current_user, destination=clicked
            )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            pass
        except Exception:
            db.session.rollback()
            raise

        if complete:
            url = url_for('conductor.edit', contract_id=mod_contract.id)
        else:
            url = url_for('conductor.detail', contract_id=contract_id, stage_id=stage.id)

        return redirect(url)

    elif request.args.get('extend'):
        extended_contract = extend_a_contract(child_contract_id=contract_id, delete_child=True)

        flash(
            'Contract Successfully extended! Please update it with a new expiration date',
            'alert-success'
        )

        return redirect(url_for(
            'conductor.edit', contract_id=extended_contract.id
        ))

    elif request.args.get('flow_switch'):
        new_contract_stage = switch_flow(
            int(request.args.get('flow_switch')), contract_id, current_user
        )
        return redirect(url_for(
            'conductor.detail', contract_id=contract_id, stage_id=new_contract_stage.id
        ))

    if stage_id == -1:
        # redirect to the current stage page
        contract_stage = ContractStage.query.join(
            ContractBase, ContractBase.id == ContractStage.contract_id
        ).filter(
            ContractStage.contract_id == contract_id,
            ContractStage.stage_id == ContractBase.current_stage_id,
            ContractStage.flow_id == ContractBase.flow_id
        ).first()

        return redirect(url_for(
            'conductor.detail', contract_id=contract_id, stage_id=contract_stage.id
        ))

    contract = ContractBase.query.get(contract_id)
    if not contract:
        abort(404)

    stages = get_contract_stages(contract)

    try:
        active_stage = [i for i in stages if i.id == stage_id][0]
        current_stage = [i for i in stages if i.entered and not i.exited][0]
        if active_stage.entered is None:
            abort(404)
    except IndexError:
        abort(404)

    note_form = NoteForm()
    update_form = SendUpdateForm()
    opportunity_form, categories, subcategories = generate_opportunity_form(
        obj=create_opp_form_obj(contract),
        form=PostOpportunityForm
    )
    metadata_form = ContractMetadataForm(obj=ContractMetadataObj(contract))

    forms = {
        'activity': note_form, 'update': update_form,
        'post': opportunity_form, 'update-metadata': metadata_form
    }

    active_tab = '#activity'

    submitted_form = request.args.get('form', None)

    if submitted_form:
        if handle_form(
            forms[submitted_form], submitted_form, stage_id,
            current_user, contract, active_stage
        ):
            return redirect(url_for(
                'conductor.detail', contract_id=contract_id, stage_id=stage_id
            ))
        else:
            active_tab = '#' + submitted_form

    actions = build_action_log(stage_id, active_stage)
    subscribers, total_subscribers = build_subscribers(contract)
    flows = Flow.query.filter(Flow.id != contract.flow_id).all()

    if len(stages) > 0:
        return render_template(
            'conductor/detail.html',
            stages=stages, actions=actions, active_tab=active_tab,
            note_form=note_form, update_form=update_form,
            opportunity_form=opportunity_form, metadata_form=metadata_form,
            contract=contract, current_user=current_user,
            active_stage=active_stage, current_stage=current_stage,
            flows=flows, subscribers=subscribers,
            total_subscribers=total_subscribers, categories=categories,
            subcategories=subcategories
        )
    abort(404)

@blueprint.route(
    '/contract/<int:contract_id>/stage/<int:stage_id>/note/<int:note_id>/delete',
    methods=['GET', 'POST']
)
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
    return redirect(url_for('conductor.detail', contract_id=contract_id))

@blueprint.route('/contract/<int:contract_id>/edit/contract', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit(contract_id):
    '''Update information about a contract
    '''
    contract = ContractBase.query.get(contract_id)

    # clear the contract from our session
    session.pop('contract', None)

    if contract:
        form = EditContractForm(obj=contract)
        if form.validate_on_submit():
            session['contract'] = json.dumps(form.data, default=json_serial)
            return redirect(url_for('conductor.edit_company', contract_id=contract.id))
        form.spec_number.data = contract.get_spec_number().value
        return render_template('conductor/edit/edit.html', form=form, contract=contract)
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit/company', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit_company(contract_id):
    contract = ContractBase.query.get(contract_id)

    if contract and session.get('contract') is not None:
        form = CompanyListForm()
        if form.validate_on_submit():
            cleaned = parse_companies(form.data)
            session['companies'] = json.dumps(cleaned, default=json_serial)
            return redirect(url_for('conductor.edit_company_contacts', contract_id=contract.id))
        return render_template('conductor/edit/edit_company.html', form=form, contract=contract)
    elif session.get('contract') is None:
        return redirect(url_for('conductor.edit', contract_id=contract_id))
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit/contacts', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit_company_contacts(contract_id):
    contract = ContractBase.query.get(contract_id)

    if contract and session.get('contract') is not None and session.get('companies') is not None:
        form = CompanyContactListForm()
        companies = json.loads(session['companies'])
        if form.validate_on_submit():
            flash('Contract Successfully Updated!', 'alert-success')
            Notification(
                to_email=[i.email for i in contract.followers],
                from_email=current_user.email,
                subject='A contract you follow has been updated!',
                html_template='conductor/emails/new_contract.html',
                contract=contract
            ).send(multi=True)

        for company in companies:
            form.companies.append_entry(data=company['company_name'])

        return render_template(
            'conductor/edit/edit_company_contacts.html', form=form, contract=contract,
            companies=companies
        )
    elif session.get('contract') is None:
        return redirect(url_for('conductor.edit', contract_id=contract_id))
    elif session.get('companies') is None:
        return redirect(url_for('conductor.edit_company', contract_id=contract_id))
    abort(404)


# @blueprint.route('')
# @requires_roles('conductor', 'admin', 'superadmin')
# def flows():
    # pass

# @blueprint.route('')
# @requires_roles('conductor', 'admin', 'superadmin')
# def stages():
#     pass

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
    '''Assign & start work on a contract to an admin or a conductor
    '''
    contract = ContractBase.query.get(contract_id)
    flow = Flow.query.get(flow_id)

    # if we don't have a flow, stop and throw an error
    if not flow:
        flash('Something went wrong! That flow doesn\'t exist!', 'alert-danger')
        return redirect('conductor.index')

    # if the contract is already assigned,
    # resassign it and continue on
    if contract.assigned_to:
        contract.assigned_to = user_id
    # otherwise, it's new work. perform the following:
    # 1. create a cloned version of the contract
    # 2. create the relevant contract stages
    # 3. transition into the first stage
    # 4. assign the contract to the user
    else:
        contract = clone_a_contract(contract)
        try:
            stages, _, _ = create_contract_stages(flow_id, contract.id, contract=contract)
            _, new_contract, _ = transition_stage(
                contract.id, current_user, contract=contract, stages=stages
            )
            db.session.commit()
        except IntegrityError, e:
            # we already have the sequence for this, so just
            # rollback and pass
            db.session.rollback()
            pass
        except Exception, e:
            flash('Something went wrong! {}'.format(e.message), 'alert-danger')
            abort(500)

        new_contract.assigned_to = user_id

    db.session.commit()
    flash('Successfully assigned to {}!'.format(contract.assigned.email), 'alert-success')
    return redirect(url_for('conductor.index'))
