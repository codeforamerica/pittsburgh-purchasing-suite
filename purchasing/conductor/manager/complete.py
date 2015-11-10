# -*- coding: utf-8 -*-

import json
import urllib2

from flask import (
    session, redirect, url_for, current_app,
    render_template, abort, request, jsonify
)
from flask_login import current_user

from purchasing.decorators import requires_roles
from purchasing.database import db, get_or_create
from purchasing.notifications import Notification

from purchasing.data.contracts import ContractBase
from purchasing.data.companies import Company, CompanyContact

from purchasing.conductor.forms import (
    EditContractForm, CompanyListForm,
    CompanyContactListForm
)
from purchasing.conductor.util import parse_companies, json_serial

from purchasing.conductor.manager import blueprint

@blueprint.route('/contract/<int:contract_id>/edit/contract', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit(contract_id):
    '''Update information about a contract
    '''
    contract = ContractBase.query.get(contract_id)
    completed_last_stage = contract.completed_last_stage()

    # clear the contract/companies from our session
    session.pop('contract-{}'.format(contract_id), None)
    session.pop('companies-{}'.format(contract_id), None)

    extend = session.get('extend-{}'.format(contract_id), None)

    if contract and completed_last_stage or extend:
        form = EditContractForm(obj=contract)
        if form.validate_on_submit():
            if not extend:
                session['contract-{}'.format(contract_id)] = json.dumps(form.data, default=json_serial)
                return redirect(url_for('conductor.edit_company', contract_id=contract.id))
            else:
                # if there is no flow, that means that it is an extended contract
                # so we will save it and return back to the conductor home page
                contract.update_with_spec_number(form.data)
                current_app.logger.info('CONDUCTOR CONTRACT COMPLETE - contract metadata for "{}" updated'.format(
                    contract.description
                ))
                session.pop('extend-{}'.format(contract_id))
                return redirect(url_for('conductor.index'))
        form.spec_number.data = contract.get_spec_number().value
        return render_template('conductor/edit/edit.html', form=form, contract=contract)
    elif not completed_last_stage:
        return redirect(url_for('conductor.detail', contract_id=contract.id))
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit/company', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit_company(contract_id):
    '''
    '''
    contract = ContractBase.query.get(contract_id)

    if contract and session.get('contract-{}'.format(contract_id)) is not None:
        form = CompanyListForm()
        if form.validate_on_submit():
            cleaned = parse_companies(form.data)
            session['companies-{}'.format(contract_id)] = json.dumps(cleaned, default=json_serial)
            current_app.logger.info('CONDUCTOR CONTRACT COMPLETE - awarded companies for contract "{}" assigned'.format(
                contract.description
            ))
            return redirect(url_for('conductor.edit_company_contacts', contract_id=contract.id))
        return render_template('conductor/edit/edit_company.html', form=form, contract=contract)
    elif session.get('contract-{}'.format(contract_id)) is None:
        return redirect(url_for('conductor.edit', contract_id=contract_id))
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit/contacts', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def edit_company_contacts(contract_id):
    '''
    '''
    contract = ContractBase.query.get(contract_id)

    if contract and session.get('contract-{}'.format(contract_id)) is not None and session.get('companies-{}'.format(contract_id)) is not None:
        form = CompanyContactListForm()

        # pull out companies from session, order them by financial id
        # so that they can be grouped appropriately
        companies = sorted(
            json.loads(session['companies-{}'.format(contract_id)]),
            key=lambda x: x.get('financial_id')
        )

        if form.validate_on_submit():
            main_contract = contract
            for ix, _company in enumerate(companies):
                contract_data = json.loads(session['contract-{}'.format(contract_id)])
                # because multiple companies can have the same name, don't use
                # get_or_create because it can create multiples
                if _company.get('company_id') > 0:
                    company = Company.query.get(_company.get('company_id'))
                else:
                    company = Company.create(company_name=_company.get('company_name'))
                # contacts should be unique to companies, though
                try:
                    for _contact in form.data.get('companies')[ix].get('contacts'):
                        _contact['company_id'] = company.id
                        contact, _ = get_or_create(db.session, CompanyContact, **_contact)
                # if there are no contacts, an index error will be thrown for this company
                # so we catch it and just pass
                except IndexError:
                    pass

                contract_data['financial_id'] = _company['financial_id']

                if contract.financial_id is None or contract.financial_id == _company['financial_id']:
                    contract.update_with_spec_number(contract_data, company=company)
                else:
                    contract = ContractBase.clone(contract, parent_id=contract.parent_id, strip=False)
                    contract.update_with_spec_number(contract_data, company=company)

                contract.is_visible = True
                db.session.commit()

            Notification(
                to_email=[i.email for i in contract.followers],
                from_email=current_app.config['CONDUCTOR_SENDER'],
                reply_to=current_user.email,
                subject='A contract you follow has been updated!',
                html_template='conductor/emails/new_contract.html',
                contract=main_contract
            ).send(multi=True)

            session.pop('contract-{}'.format(contract_id))
            session.pop('companies-{}'.format(contract_id))
            session['success-{}'.format(contract_id)] = True

            current_app.logger.info('''
CONDUCTOR CONTRACT COMPLETE - company contacts for contract "{}" assigned. |New contract(s) successfully created'''.format(
                contract.description
            ))

            if contract.parent:
                contract.parent.complete()

            return redirect(url_for('conductor.success', contract_id=main_contract.id))

        if len(form.companies.entries) == 0:
            for company in companies:
                form.companies.append_entry()

        return render_template(
            'conductor/edit/edit_company_contacts.html', form=form, contract=contract,
            companies=companies
        )
    elif session.get('contract-{}'.format(contract_id)) is None:
        return redirect(url_for('conductor.edit', contract_id=contract_id))
    elif session.get('companies-{}'.format(contract_id)) is None:
        return redirect(url_for('conductor.edit_company', contract_id=contract_id))
    abort(404)

@blueprint.route('/contract/<int:contract_id>/edit/success', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def success(contract_id):
    '''
    '''
    if session.pop('success-{}'.format(contract_id), None):
        contract = ContractBase.query.get(contract_id)
        return render_template('conductor/edit/success.html', contract=contract)
    return redirect(url_for('conductor.edit_company_contacts', contract_id=contract_id))

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
