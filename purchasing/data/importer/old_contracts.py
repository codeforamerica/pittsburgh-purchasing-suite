# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import re
from purchasing.database import db, get_or_create
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from purchasing.data.importer import (
    extract, convert_empty_to_none, determine_company_contact
)

from purchasing.utils import turn_off_sqlalchemy_events, turn_on_sqlalchemy_events
from purchasing.data.contracts import ContractBase, ContractType, ContractProperty
from purchasing.data.companies import CompanyContact, Company

BASE_CONTRACT_URL = 'http://apps.county.allegheny.pa.us/BidsSearch/pdf/{number}.pdf'

def convert_contract_number(contract_number):
    _contract_number = None
    # first try to convert it to an int
    try:
        _contract_number = int(float(contract_number))
        contract_number = _contract_number
    # if you can't, it has * or other characters, so just
    # strip down to the digits
    except ValueError:
        if '**' in contract_number:
            _contract_number = int(re.sub(r'i?\D', '', contract_number))
        elif '*' in contract_number:
            _contract_number = None
        elif 'i' in contract_number:
            _contract_number = contract_number

    return _contract_number

def main(file_target='./files/2015-05-05-contractlist.csv'):
    data = extract(file_target)

    try:
        for row in data:
            # create or select the company
            try:
                turn_off_sqlalchemy_events()
            except InvalidRequestError:
                pass

            try:
                company, new_company = get_or_create(
                    db.session, Company,
                    company_name=convert_empty_to_none(row.get('COMPANY'))
                )
            except IntegrityError:
                db.session.rollback()
                company = None

            company_contact = determine_company_contact(row)

            if company_contact and company:

                # create the new company contact
                company_contact, new_contact = get_or_create(
                    db.session, CompanyContact,
                    company_id=company.id,
                    **company_contact
                )

                if new_contact:
                    db.session.add(company_contact)
                    db.session.commit()

            try:
                expiration = datetime.datetime.strptime(row.get('EXPIRATION'), '%m/%d/%y')
            except ValueError:
                expiration = None

            try:
                _financial_id = convert_empty_to_none(row.get('CONTROLLER'))
            except ValueError:
                _financial_id = None

            contract_type, _ = get_or_create(
                db.session, ContractType,
                name=convert_empty_to_none(row.get('TYPE OF CONTRACT'))
            )

            # create or select the contract object
            contract, new_contract = get_or_create(
                db.session, ContractBase,
                contract_type=contract_type,
                expiration_date=expiration,
                financial_id=_financial_id,
                description=convert_empty_to_none(row.get('SERVICE'))
            )

            if contract.contract_type == 'County':
                contract.contract_href = BASE_CONTRACT_URL.format(
                    number=convert_contract_number(convert_empty_to_none(row.get('CONTRACT')))
                )

            contract_number, new_contract_number = get_or_create(
                db.session, ContractProperty,
                contract_id=contract.id,
                key='Spec Number',
                value=convert_empty_to_none(row.get('CONTRACT'))
            )

            if new_contract_number:
                db.session.add(contract_number)

            if company:
                contract.companies.append(company)
            db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    finally:
        turn_on_sqlalchemy_events()
