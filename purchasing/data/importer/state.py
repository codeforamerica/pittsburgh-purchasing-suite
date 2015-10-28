# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
from purchasing.database import db
from sqlalchemy.exc import IntegrityError
from purchasing.data.importer import (
    extract, get_or_create, convert_empty_to_none,
    determine_company_contact
)

from purchasing.data.contracts import ContractBase, ContractType, ContractProperty
from purchasing.data.companies import CompanyContact, Company

BASE_CONTRACT_URL = 'http://www.emarketplace.state.pa.us/FileDownload.aspx?file={number}\ContractFile.pdf'

def main(file_target='./files/2015-10-27-state-contracts.csv'):
    data = extract(file_target)

    try:
        for row in data:
            # create or select the company
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
                expiration = datetime.datetime.strptime(row.get('EXPIRATION'), '%m/%d/%Y')
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
                description=convert_empty_to_none(row.get('SERVICE')),
                contract_href=BASE_CONTRACT_URL.format(
                    number=convert_empty_to_none(row.get('CONTRACT'))
                )
            )

            parent_number, new_parent_number = get_or_create(
                db.session, ContractProperty, commit=False,
                contract_id=contract.id,
                key='Parent Number',
                value=convert_empty_to_none(row.get('PARENT'))
            )

            if new_parent_number:
                db.session.add(parent_number)

            contract_number, new_contract_number = get_or_create(
                db.session, ContractProperty, commit=False,
                contract_id=contract.id,
                key='Contract Number',
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
