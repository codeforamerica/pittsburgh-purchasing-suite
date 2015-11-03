# -*- coding: utf-8 -*-

import datetime
import re
import pytz

from flask import current_app
from wtforms.validators import ValidationError

EMAIL_REGEX = re.compile(r'^.+@([^.@][^@]+)$', re.IGNORECASE)
US_PHONE_REGEX = re.compile(r'^(\d{3})-(\d{3})-(\d{4})$')

STATE_ABBREV = ('AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                'HI', 'ID', 'IL', 'IN', 'IO', 'KS', 'KY', 'LA', 'ME', 'MD',
                'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY')

def not_all_hidden(form, field):
    '''Makes sure that every field isn't blank
    '''
    if not any([v for (k, v) in form.data.items() if k != field.name]):
        raise ValidationError('You must update at least one field!')

def validate_multiple_emails(form, field):
    '''Parses a semicolon-delimited list of emails, validating each
    '''
    if field.data:
        for email in field.data.split(';'):
            if email == '':
                continue
            elif not re.match(EMAIL_REGEX, email):
                raise ValidationError('One of the supplied emails is invalid!')

def validate_different(form, field):
    '''Ensures that all subfields have a different value
    '''
    if field.data:
        if len(field.data) == len(set(field.data)):
            pass
        else:
            raise ValidationError('You cannot have duplicate stages!')

def get_default():
    return pytz.UTC.localize(
        datetime.datetime.utcnow()
    ).astimezone(current_app.config['DISPLAY_TIMEZONE'])

def validate_integer(form, field):
    if field.data:
        try:
            int(field.data)
        except:
            raise ValidationError('This must be an integer!')

def validate_date(form, field):
    if field.data:
        utc_data = current_app.config['DISPLAY_TIMEZONE'].localize(field.data).astimezone(pytz.UTC).replace(tzinfo=None)
        if utc_data < form.started or utc_data > form.maximum:
            raise ValidationError("Date conflicts! Replaced with today's date.")
