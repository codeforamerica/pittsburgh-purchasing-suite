# -*- coding: utf-8 -*-

import csv

def extract(file_target, first_row_headers=[]):
    '''
    Pulls csv data out of a file target.

    Returns a list of strings. Takes an optional
    "first_row_headers" parameter. If this is not empty,
    it will be used as the fieldnames in the DictReader
    '''
    data = []

    with open(file_target, 'rU') as f:
        fieldnames = first_row_headers if len(first_row_headers) > 0 else None
        reader = csv.DictReader(f, fieldnames=fieldnames)
        for row in reader:
            data.append(row)

    return data

def get_or_create(session, model, commit=True, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = dict((k, v) for k, v in kwargs.iteritems())
        instance = model(**params)
        session.add(instance)
        if commit:
            session.commit()
        return instance, True
