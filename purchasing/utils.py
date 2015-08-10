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

from purchasing.database import db

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
    db.session.execute(db.text('''
        REFRESH MATERIALIZED VIEW CONCURRENTLY search_view
    '''))

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

def upload_file(filename, bucket, root=None, prefix='/static'):
    filepath = os.path.join(root, filename.lstrip('/')) if root else filename
    _file = bucket.new_key(
        '{}/{}'.format(prefix, filename)
    )
    aggressive_headers = _get_aggressive_cache_headers(_file)
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
            time.mktime((datetime.datetime.now() + datetime.timedelta(days=365 * 5)).timetuple())
        )
    )

    if 'css' in key.name.lower():
        metadata['Content-Type'] = 'text/css'
    else:
        metadata['Content-Type'] = key.content_type

    # HTTP/1.1 (5 years)
    metadata['Cache-Control'] = 'max-age=%d, public' % (3600 * 24 * 360 * 5)

    return metadata

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
