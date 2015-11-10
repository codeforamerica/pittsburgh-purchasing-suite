# -*- coding: utf-8 -*-

import re
import datetime
from difflib import SequenceMatcher as SM

from purchasing.data.importer import (
    extract, convert_empty_to_none, determine_company_contact
)

from sqlalchemy.exc import InvalidRequestError

from purchasing.utils import turn_off_sqlalchemy_events, turn_on_sqlalchemy_events
from purchasing.database import db, get_or_create
from purchasing.data.contracts import ContractBase, ContractProperty, LineItem, ContractType
from purchasing.data.companies import Company, CompanyContact

CONSTANT_FIELDS = [
    'CONTROLLER', 'Expiration', 'Company',
    'CONTACT', 'ADDRESS1', 'ADDRESS2',
    'E-MAIL ADDRESS', 'FAX #', 'PHONE #'
]

VALID_FILENAMES = re.compile(r'^(COSTARS|costars)(-| )\d+\.csv$')
JUNK_STRING = re.compile(r'((\, )?(LLC|llc))|(\(.+\))|((\, )?[Ii]nc\.?)|( ?d\.?b\.?a\.?)')

def convert_to_bool(field):
    '''Converts yes/no values to boolean

    Returns:
        True if field contains 'yes' or 'YES', False otherwise
    '''
    if field == 'Yes' or field == 'yes':
        return True
    return False

def connect_to_s3_bucket(access_key, access_secret, bucket):
    '''
    Gets a connection to an S3 bucket.
    '''
    from boto.s3.connection import S3Connection
    from boto.exception import NoAuthHandlerFound, S3ResponseError

    if not all((access_key, access_secret, bucket)):
        return

    try:
        conn = S3Connection(
            aws_access_key_id=access_key,
            aws_secret_access_key=access_secret
        )
        if conn:
            bucket = conn.get_bucket(bucket)
            return bucket
        return None

    except (NoAuthHandlerFound, S3ResponseError):
        return None

def parse_s3(bucket):
    pass

def main(filetarget, filename, access_key, access_secret, bucket):
    if not re.match(VALID_FILENAMES, filename):
        raise IOError('Not a valid filename. Filenames must have COSTARS with number separated by a dash (Ex. "COSTARS-3.csv").')

    data = extract(filetarget)
    s3_files = None

    # connect to s3 and get contents of bucket
    bucket = connect_to_s3_bucket(access_key, access_secret, bucket)
    if bucket:
        s3_files = bucket.list()

    try:
        for row in data:

            try:
                turn_off_sqlalchemy_events()
            except InvalidRequestError:
                pass

            company, new_company = get_or_create(
                db.session, Company,
                company_name=convert_empty_to_none(row.get('Company'))
            )

            company_contact = determine_company_contact(row)

            if company_contact:

                # create the new company contact
                company_contact, new_contact = get_or_create(
                    db.session, CompanyContact,
                    company_id=company.id,
                    **company_contact
                )

                if new_contact:
                    db.session.add(company_contact)
                    db.session.commit()

            costars_awardee = convert_empty_to_none(row.get('Company'))

            try:
                expiration = datetime.datetime.strptime(row.get('Expiration'), '%m/%d/%y')
            except ValueError:
                expiration = None

            costars_type, _ = get_or_create(
                db.session, ContractType,
                name='COSTARS'
            )

            # create or select the contract object
            contract, new_contract = get_or_create(
                db.session, ContractBase,
                contract_type=costars_type,
                expiration_date=expiration,
                financial_id=convert_empty_to_none(row.get('CONTROLLER')),
                description='{costars} - {company}'.format(
                    costars=filename.replace('-', ' ').rstrip('.csv').upper(),
                    company=costars_awardee
                )
            )

            # connect to s3
            if s3_files:
                # all files start with 'costars-{number}-', which we should be
                # able to get from our filename
                max_ratio = (None, 0)

                startswith = filename.strip('.csv').lower()
                for _file in s3_files:
                    _filename = _file.name.encode('utf-8').strip('.pdf').rstrip('.')
                    costars_awardee = costars_awardee.rstrip('.')

                    # because the file start patterns are consistent, strip
                    # out the costars-{number}-
                    _file_awardee = _filename.split('-')[2]

                    # check for absolute matches
                    match_ratio = SM(lambda x: bool(re.match(JUNK_STRING, x)), costars_awardee, _file_awardee).ratio()
                    if match_ratio == 1:
                        # this is an absolute match, insert it into the db and break
                        max_ratio = (_file.generate_url(expires_in=0, query_auth=False), match_ratio)
                        if _filename.startswith(startswith):
                            break
                        else:
                            continue

                    elif match_ratio > max_ratio[1]:
                        # this is the best match we have so far
                        max_ratio = (_file.generate_url(expires_in=0, query_auth=False), match_ratio)
                        continue

                # use the best match that we have
                print contract.description, max_ratio
                if max_ratio[1] > 0.7:
                    contract.contract_href = max_ratio[0]

            for k, v in row.iteritems():
                if k in CONSTANT_FIELDS:
                    continue

                # insert a new contract property with where the company is located
                elif k == 'County Located':
                    if row.get('County Located') != '':
                        county_located, new_county_located = get_or_create(
                            db.session, ContractProperty,
                            contract_id=contract.id,
                            key='Located in',
                            value=convert_empty_to_none(
                                '{county} County'.format(county=row.get('County Located'))
                            )
                        )
                    else:
                        continue

                    if new_county_located:
                        db.session.add(county_located)

                # insert a new property with the listed manufacturers
                elif k == 'Manufacturers':

                    if convert_empty_to_none(row.get('Manufacturers')):

                        manufacturer, new_manufacturer = get_or_create(
                            db.session, ContractProperty,
                            contract_id=contract.id,
                            key='List of manufacturers',
                            value=convert_empty_to_none(row.get('Manufacturers'))
                        )

                        if new_manufacturer:
                            db.session.add(manufacturer)

                # we are treating everything else like a line item,
                # so upload all of those pieces
                else:
                    if convert_to_bool(convert_empty_to_none(v)):
                        line_item, new_line_item = get_or_create(
                            db.session, LineItem,
                            contract_id=contract.id,
                            description=convert_empty_to_none(k)
                        )
                    else:
                        continue

                    if new_line_item:
                        db.session.add(line_item)

            contract.companies.append(company)
            db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    finally:
        turn_on_sqlalchemy_events()
