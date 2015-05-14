# -*- coding: utf-8 -*-

from purchasing.data.importer import extract, get_or_create, convert_empty_to_none
from purchasing.database import db
from purchasing.data.models import (
    CompanyContact,
    Company,
    ContractBase,
    ContractProperty,
    LineItem
)

CONSTANT_FIELDS = [
    'CONTROLLER', 'Expiration', 'Company',
    'CONTACT', 'ADDRESS1',  'ADDRESS2',
    'E-MAIL ADDRESS', 'FAX #', 'PHONE #'
]

def convert_to_bool(field):
    if field == 'Yes' or field == 'yes':
        return True
    return False

def main(filetarget, filename):

    data = extract(filetarget)

    try:
        for row in data:
            company, new_company = get_or_create(
                db.session, Company,
                company_name=convert_empty_to_none(row.get('Company'))
            )

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
                contract_type='COSTARS',
                expiration_date=expiration,
                financial_id=convert_empty_to_none(row.get('CONTROLLER')),
                description='{costars} - {company}'.format(
                    costars=filename.replace('_', ' ').strip('.csv'),
                    company=convert_empty_to_none(row.get('Company'))
                )
            )

            for k, v in row.iteritems():
                if k in CONSTANT_FIELDS:
                    continue

                elif k == 'County Located':
                    if row.get('County Located') != '':
                        county_located, new_county_located = get_or_create(
                            db.session, ContractProperty, commit=False,
                            contract_id=contract.id,
                            key='Located in',
                            value=convert_empty_to_none(
                                '{county} County'.format(county=row.get('County Served'))
                            )
                        )
                    else:
                        continue

                    if new_county_located:
                        db.session.add(county_located)

                elif k == 'Manufacturers':
                    manufacturer, new_manufacturer = get_or_create(
                        db.session, ContractProperty, commit=False,
                        contract_id=contract.id,
                        key='List of manufacturers',
                        value=convert_empty_to_none(row.get('Manufacturers'))
                    )

                    if new_manufacturer:
                        db.session.add(manufacturer)

                else:
                    if convert_to_bool(convert_empty_to_none(v)):
                        line_item, new_line_item = get_or_create(
                            db.session, LineItem, commit=False,
                            contract_id=contract.id,
                            description=convert_empty_to_none(k)
                        )
                    else:
                        continue

                    if new_line_item:
                        db.session.add(line_item)

            db.session.commit()

            contract.companies.append(company)
            db.session.commit()

    except Exception, e:
        db.session.rollback()
        raise e
