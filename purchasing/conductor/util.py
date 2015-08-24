# -*- coding: utf-8 -*-

import datetime
from collections import defaultdict

from flask import request
from flask_login import current_user

from purchasing.database import db
from purchasing.notifications import Notification

from purchasing.data.models import ContractStageActionItem, Flow
from purchasing.data.contracts import clone_a_contract
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
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        return obj.isoformat()

def create_opp_form_obj(contract, contact_email=None):
    if contract.opportunity:
        obj = contract.opportunity
        obj.contact_email = contract.opportunity.contact.email
    else:
        obj = OpportunityFormObj(contract.department, contract.description, contact_email)
    return obj

def update_contract_with_spec(contract, form_data, company=None, clone=False):
    if clone:
        contract = clone_a_contract(contract, parent_id=contract.parent_id, strip=False)

    spec_number = contract.get_spec_number()

    data = form_data
    new_spec = data.pop('spec_number', None)

    if new_spec:
        spec_number.key = 'Spec Number'
        spec_number.value = new_spec
    else:
        spec_number.key = 'Spec Number'
        spec_number.value = None
    contract.properties.append(spec_number)

    if company:
        contract.companies.append(company)

    contract.update(**data)

    return contract, spec_number

def parse_companies(companies):
    cleaned = []
    for company in companies.get('companies'):
        if company.get('company_name'):
            cleaned.append({
                'company_name': company.get('company_name')[1],
                'company_id': company.get('company_name')[0],
                'financial_id': company.get('controller_number')
            })
        else:
            cleaned.append({
                'company_name': company.get('new_company_name'),
                'company_id': -1,
                'financial_id': company.get('new_company_controller_number')
            })
    return cleaned

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

            _, _ = update_contract_with_spec(contract, data)
            # this process pops off the spec number, so get it back
            data['spec_number'] = form.data.get('spec_number')

            # get department
            if form.data.get('department', None):
                data['department'] = form.data.get('department').name

            action.action_detail = data

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

    if contract.parent is None:
        followers = []
    else:
        followers = [i for i in contract.parent.followers if i not in department_users]

    subscribers = {
        'Department Users': department_users,
        'Followers': followers,
        'County Purchasers': [i for i in county_purchasers if i not in department_users],
        'EORC': eorc
    }
    return subscribers, sum([len(i) for i in subscribers.values()])

def reshape_metrics_granular(resultset):
    '''Transform long data from database into wide data for consumption

    Take in a result set (list of tuples), return a dictionary of results.
    The key for the dictionary is the contract id, and the values are a list
    of (fieldname, value). Metadata (common to all rows) is listed first, and
    timing information from each stage is listed afterwords. Sorting is assumed
    to be done on the database layer
    '''
    results = defaultdict(list)
    headers = []

    for ix, row in enumerate(resultset):
        if ix == 0:
            headers.extend(['item_number', 'description', 'assigned_to', 'department'])

        # if this is a new contract row, append metadata
        if len(results[row.contract_id]) == 0:
            results[row.contract_id].extend([
                row.contract_id,
                row.description,
                row.email,
                row.department,
            ])

        # append the stage date data
        results[row.contract_id].extend([
            row.exited.date()
        ])

        if row.stage_name not in headers:
            headers.append(row.stage_name)

    return results, headers

def reshape_metrics_csv_rollup(resultset, flow_id):
    '''Transform long data from database into rollup view for quick consumption

    Take in a result set (list of tuples), and return a dictionary of key-value
    pairs for each required field.
    '''
    pass
