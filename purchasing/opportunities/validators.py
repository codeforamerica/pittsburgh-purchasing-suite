# -*- coding: utf-8 -*-

import re
import datetime

from wtforms.validators import ValidationError

from purchasing.opportunities.models import Vendor
from purchasing.users.models import User
from purchasing.public.models import AcceptedEmailDomains

ALL_INTEGERS = re.compile('[^\d.]')
DOMAINS = re.compile('@[\w.]+')

def email_present(form, field):
    '''Checks that we have a vendor with that email address
    '''
    if field.data:
        vendor = Vendor.query.filter(Vendor.email == field.data).first()
        if vendor is None:
            raise ValidationError("We can't find the email {}!".format(field.data))

def city_domain_email(form, field):
    '''Checks that the email is a current user or a city domain
    '''
    if field.data:
        user = User.query.filter(User.email == field.data).first()
        if user is None:
            domain = re.search(DOMAINS, field.data)
            if domain and AcceptedEmailDomains.valid_domain(domain.group().lstrip('@')):
                raise ValidationError("That's not a valid contact!")

def max_words(_max=500):
    '''Checks that a text-area field has fewer than the allowed number of words.

    :param _max: Maximum words allowed, defaults to 500
    '''
    message = 'Text cannot be more than {} words! You had {} words.'

    def _max_words(form, field):
        l = field.data and len(field.data.split()) or 0
        if l > _max:
            raise ValidationError(message.format(_max, l))

    return _max_words

def after_today(form, field):
    '''Checks that a date occurs after today
    '''
    if isinstance(field.data, datetime.datetime):
        to_test = field.data.date()
    elif isinstance(field.data, datetime.date):
        to_test = field.data
    else:
        raise ValidationError('This must be a date')

    if to_test <= datetime.date.today():
        raise ValidationError('The deadline has to be after today!')

def validate_phone_number(form, field):
    '''Strips out non-integer characters, checks that it is 10-digits
    '''
    if field.data:
        value = re.sub(ALL_INTEGERS, '', field.data)
        if len(value) != 10 and len(value) != 0:
            raise ValidationError('Invalid 10-digit phone number!')
