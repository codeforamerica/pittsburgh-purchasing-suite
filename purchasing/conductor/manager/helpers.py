# -*- coding: utf-8 -*-

import datetime

from flask_login import current_user

from purchasing.database import db
from purchasing.notifications import Notification

from purchasing.data.models import (
    ContractStageActionItem
)

from purchasing.users.models import User, Role, Department

class ContractMetadataObj(object):
    def __init__(self, contract):
        self.expiration_date = contract.expiration_date
        self.financial_id = contract.financial_id
        self.spec_number = contract.get_spec_number().value
        self.department = contract.department

def update_contract_with_spec(contract, form_data):
    spec_number = contract.get_spec_number()

    data = form_data
    new_spec = data.pop('spec_number', None)

    if new_spec:
        spec_number.key = 'Spec Number'
        spec_number.value = new_spec
        contract.properties.append(spec_number)

    contract.update(**data)
    return contract, spec_number

def handle_form(form, form_name, stage_id, user, contract):
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
            Notification(
                to_email=[i.strip() for i in form.data.get('send_to').split(';') if i != ''],
                from_email=current_user.email,
                cc_email=form.data.get('send_to_cc', []),
                subject=form.data.get('subject'),
                html_template='conductor/emails/email_update.html',
                body=form.data.get('body')
            ).send()

        elif form_name == 'opportunity':
            pass

        elif form_name == 'update-metadata':
            # remove the blank hidden field -- we don't need it
            data = form.data
            del data['all_blank']

            update_contract_with_spec(contract, data)
            # get department
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

    actions.extend([
        ContractStageActionItem(
            action_type='entered', action_detail=active_stage.entered,
            taken_at=active_stage.entered
        ),
        ContractStageActionItem(
            action_type='exited', action_detail=active_stage.exited,
            taken_at=active_stage.exited
        )
    ])
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
