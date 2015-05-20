# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import re
from purchasing.database import db
from purchasing.data.importer import extract, get_or_create, convert_empty_to_none
from purchasing.data.models import (
    CompanyContact,
    Company,
    ContractBase,
    ContractProperty
)

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
            company, new_company = get_or_create(
                db.session, Company,
                company_name=convert_empty_to_none(row.get('COMPANY'))
            )

            # parse some fields for the company contact
            try:
                first_name, last_name = row.get('CONTACT').split()
            except:
                first_name, last_name = None, None

            try:
                tmp = row.get('ADDRESS2')
                city = tmp.split(',')[0]
                state, zip_code = tmp.split(',')[1].split()
                if '-' in zip_code:
                    zip_code = zip_code.split('-')[0]
            except:
                city, state, zip_code = None, None, None

            try:
                expiration = datetime.datetime.strptime(data[0].get('EXPIRATION'), '%Y-%m-%d')
            except:
                expiration = None

            # create the new company contact
            company_contact, new_contact = get_or_create(
                db.session, CompanyContact,
                company_id=company.id,
                first_name=convert_empty_to_none(first_name),
                last_name=convert_empty_to_none(last_name),
                addr1=convert_empty_to_none(row.get('ADDRESS1')),
                city=convert_empty_to_none(city),
                state=convert_empty_to_none(state),
                zip_code=convert_empty_to_none(zip_code),
                phone_number=convert_empty_to_none(row.get('PHONE #')),
                fax_number=convert_empty_to_none(row.get('FAX #')),
                email=convert_empty_to_none(row.get('E-MAIL ADDRESS')),
            )
            if new_contact:
                db.session.add(company_contact)
                db.session.commit()

            # create or select the contract object
            contract, new_contract = get_or_create(
                db.session, ContractBase,
                contract_type=convert_empty_to_none(row.get('TYPE OF CONTRACT')),
                expiration_date=expiration,
                financial_id=convert_empty_to_none(row.get('CONTROLLER')),
                description=convert_empty_to_none(row.get('SERVICE'))
            )

            contract_number, new_contract_number = get_or_create(
                db.session, ContractProperty, commit=False,
                contract_id=contract.id,
                key='Spec Number',
                value=convert_empty_to_none(row.get('CONTRACT'))
            )

            if new_contract_number:
                db.session.add(contract_number)

            if contract.contract_type == 'County':
                contract_number_link, new_contract_number_link = get_or_create(
                    db.session, ContractProperty, commit=False,
                    contract_id=contract.id,
                    key='Link to Contract',
                    value=BASE_CONTRACT_URL.format(
                        number=convert_contract_number(convert_empty_to_none(row.get('CONTRACT')))
                    )
                )

                if new_contract_number_link:
                    db.session.add(contract_number_link)

            contract.companies.append(company)
            db.session.commit()

    except Exception:
        db.session.rollback()
        raise
