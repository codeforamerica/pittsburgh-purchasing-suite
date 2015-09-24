# -*- coding: utf-8 -*-
'''Helper utilities and decorators.'''

import re
import os
import random
import string
import time
import email
from math import ceil
import datetime

from boto.s3.connection import S3Connection

import sqlalchemy
from wtforms.validators import InputRequired, StopValidation

from purchasing.database import db, LISTEN_FOR_EVENTS

# modified from https://gist.github.com/bsmithgall/372de43205804a2279c9
SMALL_WORDS = re.compile(r'^(a|an|and|as|at|but|by|en|etc|for|if|in|nor|of|on|or|per|the|to|vs?\.?|via)$', re.I)
SPACE_SPLIT = re.compile(r'[\t ]')
# taken from http://stackoverflow.com/a/267405
CAP_WORDS = re.compile(r'^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$|(^COSTARS$)|(^PA$)|(^PQ$)|(^LLC$)')
PUNC_REGEX = re.compile(r'[{}]'.format(re.escape(string.punctuation)))
# taken from python-titlecase: https://github.com/ppannuto/python-titlecase/blob/master/titlecase/__init__.py#L27
UC_INITIALS = re.compile(r'^(?:[A-Z]{1}\.{1}|[A-Z]{1}\.{1}[A-Z]{1})+$', re.I)

TRIGGER_TUPLES = [
    ('contract', 'description'),
    ('company', 'company_name'),
    ('contract_property', 'value'),
    ('line_item', 'description'),
]

def disable_triggers():
    for table, column in TRIGGER_TUPLES:
        db.session.execute(db.text('''
            ALTER TABLE {table} DISABLE TRIGGER USER
        '''.format(table=table, column=column)))

def enable_triggers():
    for table, column in TRIGGER_TUPLES:
        db.session.execute(db.text('''
            ALTER TABLE {table} ENABLE TRIGGER USER
        '''.format(table=table, column=column)))

def refresh_search_view():
    '''Create and execute a refresh to the search view in a scoped session
    '''
    print 'Refreshing the search view...'
    session = db.create_scoped_session()
    session.execute(db.text('''
        REFRESH MATERIALIZED VIEW CONCURRENTLY search_view
    '''))
    session.commit()
    db.engine.dispose()

def get_all_refresh_mixin_models():
    # import data models for turning off/on sqlalchemy events
    from purchasing.database import RefreshSearchViewMixin
    return RefreshSearchViewMixin.__subclasses__()

def turn_off_sqlalchemy_events():
    print 'Disabling sqlalchemy events...'
    models = get_all_refresh_mixin_models()
    for model in models:
        for event in LISTEN_FOR_EVENTS:
            sqlalchemy.event.remove(model, event, model.event_handler)

def turn_on_sqlalchemy_events():
    print 'Enabling sqlalchemy events...'
    models = get_all_refresh_mixin_models()
    for model in models:
        for event in LISTEN_FOR_EVENTS:
            sqlalchemy.event.listen(model, event, model.event_handler)

def random_id(n):
    '''Returns random id of length n

    Taken from: http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python/2257449#2257449
    '''
    return ''.join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n)
    )

def connect_to_s3(access_key, access_secret, bucket_name):
    conn = S3Connection(
        aws_access_key_id=access_key,
        aws_secret_access_key=access_secret
    )
    bucket = conn.get_bucket(bucket_name)
    return conn, bucket

def upload_file(filename, bucket, input_file=None, root=None, prefix='/static', from_file=False):
    filepath = os.path.join(root, filename.lstrip('/')) if root else filename
    _file = bucket.new_key(
        '{}/{}'.format(prefix, filename)
    )
    aggressive_headers = _get_aggressive_cache_headers(_file)
    if from_file:
        _file.set_contents_from_file(input_file, headers=aggressive_headers, replace=True)
    else:
        _file.set_contents_from_filename(filepath, headers=aggressive_headers)
    _file.set_acl('public-read')
    return _file.generate_url(expires_in=0, query_auth=False)

def _get_aggressive_cache_headers(key):
    '''
    Utility for setting file expiry headers on S3
    '''
    metadata = key.metadata

    # HTTP/1.0 (5 years)
    metadata['Expires'] = '{} GMT'.format(
        email.Utils.formatdate(
            time.mktime((datetime.datetime.utcnow() + datetime.timedelta(days=365 * 5)).timetuple())
        )
    )

    if 'css' in key.name.lower():
        metadata['Content-Type'] = 'text/css'
    else:
        metadata['Content-Type'] = key.content_type

    # HTTP/1.1 (5 years)
    metadata['Cache-Control'] = 'max-age=%d, public' % (3600 * 24 * 360 * 5)

    return metadata

def build_downloadable_groups(val, iterable):
    '''Sorts and dedupes related lists

    Handles quoting, deduping, and sorting
    '''
    return '"' + '; '.join(
        sorted(list(set([i.__dict__[val] for i in iterable])))
    ) + '"'

class SimplePagination(object):
    '''
    Simple pagination support
    '''
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

class RequiredIf(InputRequired):
    # a validator which makes a field required if
    # another field is set and has a truthy value
    # http://stackoverflow.com/questions/8463209/how-to-make-a-field-conditionally-optional-in-wtforms
    # thanks to Team RVA for pointing this out

    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(
                'no field named "%s" in form' %
                other_field.label.text if other_field.label else self.other_field_name
            )
        if bool(other_field.data) and not bool(field.data):
            raise StopValidation(
                'You must also fill out "%s" if you want to fill this out.' %
                other_field.label.text if other_field.label else self.other_field_name
            )

class RequiredNotBoth(InputRequired):
    # a validator which makes forces only one between two choices
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredNotBoth, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(
                'no field named "%s" in form' %
                other_field.label.text if other_field.label else self.other_field_name
            )
        if bool(other_field.data) and bool(field.data):
            raise StopValidation(
                'You cannot choose both this and "%s"' %
                other_field.label.text if other_field.label else self.other_field_name
            )

class RequiredOne(InputRequired):
    # a validator that forces you to choose at least one
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredOne, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(
                'no field named "%s" in form' %
                other_field.label.text if other_field.label else self.other_field_name
            )
        if not bool(other_field.data) and not bool(field.data):
            raise StopValidation(
                'You must fill out either this or "%s"' %
                other_field.label.text if other_field.label else self.other_field_name
            )
