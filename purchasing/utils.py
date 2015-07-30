# -*- coding: utf-8 -*-
'''Helper utilities and decorators.'''

import os
import random
import string
import time
import email
from math import ceil
from datetime import datetime, timedelta

from flask import flash, request, url_for
from flask_login import current_user
from boto.s3.connection import S3Connection

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
            time.mktime((datetime.now() + timedelta(days=365 * 5)).timetuple())
        )
    )

    if 'css' in key.name.lower():
        metadata['Content-Type'] = 'text/css'
    else:
        metadata['Content-Type'] = key.content_type

    # HTTP/1.1 (5 years)
    metadata['Cache-Control'] = 'max-age=%d, public' % (3600 * 24 * 360 * 5)

    return metadata

def flash_errors(form, category="warning"):
    '''Flash all errors for a form.'''
    for field, errors in form.errors.items():
        for error in errors:
            flash("{0} - {1}".format(
                getattr(form, field).label.text, error), category
            )

def format_currency(value):
    return "${:,.2f}".format(value)

def url_for_other_page(page):
    args = dict(request.view_args.items() + request.args.to_dict().items())
    args['page'] = page
    return url_for(request.endpoint, **args)

def thispage():
    try:
        args = dict(request.view_args.items() + request.args.to_dict().items())
        args['thispage'] = '{path}?{query}'.format(
            path=request.path, query=request.query_string
        )
        return url_for(request.endpoint, **args)
    # pass for favicon
    except AttributeError:
        pass

def _current_user():
    args = dict(request.view_args.items() + request.args.to_dict().items())
    args['_current_user'] = current_user
    return url_for(request.endpoint, **args)

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
