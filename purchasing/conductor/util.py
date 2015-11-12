# -*- coding: utf-8 -*-

import datetime
import os

from sqlalchemy.exc import IntegrityError

from werkzeug import secure_filename

from flask import current_app
from flask_login import current_user

from purchasing.database import db
from purchasing.filters import better_title
from purchasing.utils import connect_to_s3, upload_file

from purchasing.data.contracts import ContractBase, ContractType
from purchasing.users.models import Department

class ContractMetadataObj(object):
    '''Base object to populate the contract metadata form

    Sets the expiration date, financial id, spec number, and
    department on the contract metadata form

    Arguments:
        contract: The :py:class:`~purchasing.data.contracts.ContractBase`
            contract that is currently being worked
            on, will be used to pre-populate the relevant form

    See Also:
        :py:class:`~purchasing.conductor.forms.ContractMetadataForm`
    '''
    def __init__(self, contract):
        self.expiration_date = contract.expiration_date
        self.financial_id = contract.financial_id
        self.spec_number = contract.get_spec_number().value
        self.department = contract.department

class UpdateFormObj(object):
    '''Base object to populate the send email update form

    Sets the cc email as the current user's email, and sets
    the email body as the default message from the passed
    :py:class:`~purchasing.data.stages.Stage`,
    or an empty string.

    Arguments:
        stage: a :py:class:`~purchasing.data.stages.Stage`
            object

    See Also:
        :py:class:`~purchasing.conductor.forms.SendUpdateForm`
    '''
    def __init__(self, stage):
        self.send_to_cc = current_user.email
        self.body = stage.default_message if stage.default_message else ''

class ConductorToBeaconObj(object):
    '''Base object to populate posting from Conductor to Beacon

    Sets the title of the opportunity as the contract's description,
    and then sets the default opportunity type and department from
    the app's configuration.

    Arguments:
        contract: The :py:class:`~purchasing.data.contracts.ContractBase`
            contract that is currently being worked
            on, will be used to pre-populate the relevant form

    See Also:
        :py:class:`~purchasing.conductor.forms.PostOpportunityForm`
    '''
    def __init__(self, contract):
        self.title = better_title(contract.description)
        self.opportunity_type = ContractType.get_type(current_app.config.get('CONDUCTOR_TYPE', ''))
        self.department = Department.get_dept(current_app.config.get('CONDUCTOR_DEPARTMENT', ''))

def json_serial(obj):
    '''Add JSON serialization support for datetime and date objects

    Arguments:
        obj: Object to serialize into JSON

    Returns:
        If obj is a datetime or date object, serialize it by converting it
        into an isoformat string. Otherwise, return the object itself
    '''
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        return obj.isoformat()
    return obj

def parse_companies(companies):
    '''Normalize new and existing companies into Contract model fields

    Arguments:
        companies: A list of companies and new companies
            passed in from the user's session.

    Returns:
        A list of dictionaries, normalized to be added as
        properties to a new
        :py:class:`~purchasing.data.contracts.ContractBase`
        object
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
    '''Assign a contract a flow and a user

    If a flow is passed in, the following steps are performed:

    1. If the ``clone`` flag is set to True, make a new cloned copy of the
       passed :py:class:`~purchasing.data.contracts.ContractBase`
    2. Try to get or create the contract stages for the passed
       :py:class:`~purchasing.data.flows.Flow`
    3. Inspect the output for the "revert" flag -- if the flag is set,
       that means that we are resetting the entry time on the first stage.
       In order to do this, we clear out the current stage information, which
       will make the contract transition to the first stage of it's flow
    4. If that raises an error, it is because something went wrong
       with the creation/getting of the contract stages
    5. Assign the contract's flow to the passed
       :py:class:`~purchasing.data.flows.Flow` and its assigned user to
       the passed :py:class:`~purchasing.users.models.User` and commit

    See Also:
        * :py:meth:`~purchasing.data.flows.Flow.create_contract_stages`
          for how stages are gotten/created
        * :py:meth:`~purchasing.data.contracts.ContractBase.transition`
          for how the contract handles transitioning into different stages

    Arguments:
        contract: A :py:class:`~purchasing.data.contracts.ContractBase` object
            to assign
        flow: A :py:class:`~purchasing.data.flows.Flow` object to assign
        user: A :py:class:`~purchasing.users.models.User` object to assign

    Keyword Arguments:
        start_time: An optional start time for starting work on the
            :py:class:`~purchasing.data.contracts.ContractBase`
            when it starts its first
            :py:class:`~purchasing.data.contract_stages.ContractStage`
        clone: A boolean flag of whether or not to make a clone of
            the passed :py:class:`~purchasing.data.contracts.ContractBase`

    Returns:
        An assigned :py:class:`~purchasing.data.contracts.ContractBase` if we
        are given a flow, False otherwise
    '''
    # if we don't have a flow, stop
    if not flow:
        return False

    if clone:
        contract = ContractBase.clone(contract)
        db.session.add(contract)
        db.session.commit()

    try:
        stages, _, revert = flow.create_contract_stages(contract)

        if revert and start_time and contract.get_first_stage().id == contract.current_stage_id:
            contract.current_stage = None
            contract.current_stage_id = None

        actions = contract.transition(user, complete_time=start_time)
        for i in actions:
            db.session.add(i)
        db.session.flush()
    except IntegrityError:
        # we already have the sequence for this, so just
        # rollback and pass
        db.session.rollback()
        pass

    contract.flow = flow
    contract.assigned_to = user.id
    db.session.commit()

    current_app.logger.info('CONDUCTOR ASSIGN - new contract "{}" assigned to {} with flow {}'.format(
        contract.description, contract.assigned.email, contract.flow.flow_name
    ))

    return contract

def convert_to_str(field):
    return str(field) if field else ''

def upload_costars_contract(_file):
    '''Upload a COSTARS pdf document to S3

    Arguments:
        _file: A werkzeug `FileStorage`_ object

    Returns:
        A two-tuple of (the name of the uploaded file, the path/url to the file)
    '''
    filename = secure_filename(_file.filename)

    if current_app.config['UPLOAD_S3']:
        conn, bucket = connect_to_s3(
            current_app.config['AWS_ACCESS_KEY_ID'],
            current_app.config['AWS_SECRET_ACCESS_KEY'],
            'costars'
        )

        file_href = upload_file(filename, bucket, input_file=_file, prefix='/', from_file=True)
        return filename, file_href

    else:
        try:
            os.mkdir(current_app.config['UPLOAD_DESTINATION'])
        except:
            pass

        filepath = os.path.join(current_app.config['UPLOAD_DESTINATION'], filename)
        _file.save(filepath)
        return filename, filepath
