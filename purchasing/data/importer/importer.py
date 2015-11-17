# -*- coding: utf-8 -*-

import csv

def convert_empty_to_none(val):
    '''Converts empty or "None" strings to None Types

    Arguments:
        val: The field to be converted

    Returns:
        The passed value if the value is not an empty string or
        'None', ``None`` otherwise.
    '''
    return val if val not in ['', 'None'] else None

def extract(file_target, first_row_headers=[]):
    '''Pulls csv data out of a file target.

    Arguments:
        file_target: a file object

    Keyword Arguments:
        first_row_headers: An optional list of headers that can
            be used as the keys in the returned DictReader

    Returns:
        A :py:class:`~csv.DictReader` object.
    '''
    data = []

    with open(file_target, 'rU') as f:
        fieldnames = first_row_headers if len(first_row_headers) > 0 else None
        reader = csv.DictReader(f, fieldnames=fieldnames)
        for row in reader:
            data.append(row)

    return data

def determine_company_contact(row):
    '''Convert input data to

    Arguments:
        row: An input row of data from an input spreadsheet

    Returns:
        A dict object which can be used to create a new
        :py:class:`~purchasing.data.companies.CompanyContact`
        object
    '''
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

    _first_name = convert_empty_to_none(first_name)
    _last_name = convert_empty_to_none(last_name)
    _addr1 = convert_empty_to_none(row.get('ADDRESS1'))
    _city = convert_empty_to_none(city)
    _state = convert_empty_to_none(state)
    _zip_code = convert_empty_to_none(zip_code)
    _phone_number = convert_empty_to_none(row.get('PHONE #'))
    _fax_number = convert_empty_to_none(row.get('FAX #'))
    _email = convert_empty_to_none(row.get('E-MAIL ADDRESS'))

    if any(
        (_first_name, _last_name, _addr1, _city, _state, _zip_code, _phone_number, _fax_number, _email)
    ):
        return (dict(
            first_name=_first_name, last_name=_last_name,
            addr1=_addr1, city=_city, state=_state,
            zip_code=_zip_code, phone_number=_phone_number,
            fax_number=_fax_number, email=_email
        ))

    return None
