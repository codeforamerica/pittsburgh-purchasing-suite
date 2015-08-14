# -*- coding: utf-8 -*-

import datetime
import json

from flask import request
from flask_login import current_user

from purchasing.database import db
from purchasing.notifications import Notification

from purchasing.data.models import ContractStageActionItem
from purchasing.opportunities.models import Opportunity
from purchasing.users.models import User, Role, Department

from purchasing.opportunities.util import (
    build_opportunity, fix_form_categories
)

class ContractMetadataObj(object):
    def __init__(self, contract):
        self.expiration_date = contract.expiration_date
        self.financial_id = contract.financial_id
        self.spec_number = contract.get_spec_number().value
        self.department = contract.department

class OpportunityFormObj(object):
    def __init__(self, department, title, contact_email=None):
        self.department = department
        self.title = title
        self.contact_email = contact_email

def json_serial(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()

def create_opp_form_obj(contract, contact_email=None):
    if contract.opportunity:
        obj = contract.opportunity
        obj.contact_email = contract.opportunity.contact.email
    else:
        obj = OpportunityFormObj(contract.department, contract.description, contact_email)
    return obj

def update_contract_with_spec(contract, form_data, company=None):
    spec_number = contract.get_spec_number()

    data = form_data
    new_spec = data.pop('spec_number', None)

    if new_spec:
        spec_number.key = 'Spec Number'
        spec_number.value = new_spec
        contract.properties.append(spec_number)

    if company:
        contract.companies.append(company)

    contract.update(**data)

    return contract, spec_number

def get_or_create_company_contact(form_data):
    pass

def handle_form(form, form_name, stage_id, user, contract, current_stage):
    if form.validate_on_submit():
        action = ContractStageActionItem(
            contract_stage_id=stage_id, action_type=form_name,
            taken_by=user.id, taken_at=datetime.datetime.now()
        )
        if form_name == 'activity':
            action.action_detail = {
                'note': form.data.get('note', ''),
                'stage_name': current_stage.name
            }

        elif form_name == 'update':
            action.action_detail = {
                'sent_to': form.data.get('send_to', ''),
                'body': form.data.get('body'),
                'subject': form.data.get('subject'),
                'stage_name': current_stage.name
            }
            Notification(
                to_email=[i.strip() for i in form.data.get('send_to').split(';') if i != ''],
                from_email=current_user.email,
                cc_email=form.data.get('send_to_cc', []),
                subject=form.data.get('subject'),
                html_template='conductor/emails/email_update.html',
                body=form.data.get('body')
            ).send()

        elif form_name == 'post':
            label = 'created'
            if contract.opportunity:
                label = 'updated'

            form_data = fix_form_categories(request, form, Opportunity, None)
            # add the contact email, documents back on because it was stripped by the cleaning
            form_data['contact_email'] = form.data.get('contact_email')
            form_data['documents'] = form.documents
            # add the created_by_id
            form_data['created_from_id'] = contract.id
            # strip the is_public field from the form data, it's not part of the form
            form_data.pop('is_public')
            opportunity = build_opportunity(
                form_data, publish=request.form.get('save_type'), opportunity=contract.opportunity
            )

            action.action_detail = {
                'opportunity_id': opportunity.id, 'title': opportunity.title,
                'label': label
            }

        elif form_name == 'update-metadata':
            # remove the blank hidden field -- we don't need it
            data = form.data
            del data['all_blank']

            update_contract_with_spec(contract, data)
            # get department
            data['department'] = form.data.get('department').name
            action.action_detail = data.update({'stage_name': current_stage.name})

        else:
            return False

        db.session.add(action)
        db.session.commit()
        return True

    return False

def build_action_log(stage_id, active_stage):
    '''Builds and properly orders an action log for a given stage
    '''
    actions = ContractStageActionItem.query.filter(
        ContractStageActionItem.contract_stage_id == stage_id
    ).order_by(db.text('taken_at asc')).all()

    actions = sorted(actions, key=lambda stage: stage.get_sort_key())

    return actions

def build_subscribers(contract):
    department_users = User.query.filter(
        User.department_id == contract.department_id,
        db.func.lower(Department.name) != 'equal opportunity review commission'
    ).all()

    county_purchasers = User.query.join(Role).filter(
        Role.name == 'county'
    ).all()

    eorc = User.query.join(Department).filter(
        db.func.lower(Department.name) == 'equal opportunity review commission'
    ).all()

    subscribers = {
        'Department Users': department_users,
        'Followers': [i for i in contract.parent.followers if i not in department_users],
        'County Purchasers': [i for i in county_purchasers if i not in department_users],
        'EORC': eorc
    }
    return subscribers, sum([len(i) for i in subscribers.values()])
