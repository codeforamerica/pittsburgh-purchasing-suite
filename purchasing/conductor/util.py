# -*- coding: utf-8 -*-

import datetime

from sqlalchemy.exc import IntegrityError

from flask import current_app
from flask_login import current_user

from purchasing.database import db
from purchasing.filters import better_title

from purchasing.data.contracts import ContractBase, ContractType
from purchasing.users.models import Department

class ContractMetadataObj(object):
    '''
    '''
    def __init__(self, contract):
        self.expiration_date = contract.expiration_date
        self.financial_id = contract.financial_id
        self.spec_number = contract.get_spec_number().value
        self.department = contract.department

class OpportunityFormObj(object):
    '''
    '''
    def __init__(self, department, title, contact_email=None):
        self.department = department
        self.title = title
        self.contact_email = contact_email

class UpdateFormObj(object):
    '''
    '''
    def __init__(self, stage):
        self.send_to_cc = current_user.email
        self.body = stage.default_message if stage.default_message else ''


class ConductorObj(object):
    '''
    '''
    def __init__(self, contract):
        self.title = better_title(contract.description)
        self.opportunity_type = ContractType.get_type(current_app.config.get('CONDUCTOR_TYPE', ''))
        self.department = Department.get_dept(current_app.config.get('CONDUCTOR_DEPARTMENT', ''))

def json_serial(obj):
    '''
    '''
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        return obj.isoformat()

def create_opp_form_obj(contract, contact_email=None):
    '''
    '''
    if contract.opportunity:
        obj = contract.opportunity
        obj.contact_email = contract.opportunity.contact.email
    else:
        obj = OpportunityFormObj(contract.department, contract.description, contact_email)
    return obj

def parse_companies(companies):
    '''
    '''
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

def assign_a_contract(contract, flow, user, start_time=None, clone=True):
    '''
    '''
    # if we don't have a flow, stop and throw an error
    if not flow:
        return False

    # if the contract is already assigned,
    # resassign it and continue on
    if contract.assigned_to and not contract.completed_last_stage():
        contract.assigned_to = user.id

        if start_time:
            # if we have a start time, we are modifying the first
            # stage start time. check to make sure that we are
            # actually in the correct stage, then nuke the current
            # stage and transition into the first stage with the
            # new time
            first_stage = contract.get_first_stage()
            if first_stage.stage_id == contract.current_stage_id:
                contract.current_stage = None
                contract.current_stage_id = None

                actions = contract.transition(user, complete_time=start_time)
                for i in actions:
                    db.session.add(i)
                db.session.flush()

        db.session.commit()

        current_app.logger.info('CONDUCTOR ASSIGN - old contract "{}" assigned to {} with flow {}'.format(
            contract.description, contract.assigned.email, contract.flow.flow_name
        ))

        return contract

    # otherwise, it's new work. perform the following:
    # 1. create a cloned version of the contract
    # 2. create the relevant contract stages
    # 3. transition into the first stage
    # 4. assign the contract to the user
    else:
        if clone:
            contract = ContractBase.clone(contract)
            db.session.add(contract)
            db.session.commit()
        try:
            stages, _, _ = flow.create_contract_stages(contract)
            actions = contract.transition(user, complete_time=start_time)
            for i in actions:
                db.session.add(i)
            db.session.flush()
        except IntegrityError:
            # we already have the sequence for this, so just
            # rollback and pass
            db.session.rollback()
            pass

        contract.assigned_to = user.id
        db.session.commit()

        current_app.logger.info('CONDUCTOR ASSIGN - new contract "{}" assigned to {} with flow {}'.format(
            contract.description, contract.assigned.email, contract.flow.flow_name
        ))

        return contract

def convert_to_str(field):
    return str(field) if field else ''
