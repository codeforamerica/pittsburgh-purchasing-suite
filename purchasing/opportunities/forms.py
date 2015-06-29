# -*- coding: utf-8 -*-

import re
import datetime

from flask import current_app
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms import widgets, fields
from wtforms.validators import DataRequired, Email, ValidationError

from purchasing.opportunities.models import Category, Vendor

from purchasing.users.models import DEPARTMENT_CHOICES, User

ALL_INTEGERS = re.compile('[^\d.]')
DOMAINS = re.compile('@[\w.]+')

class MultiCheckboxField(fields.SelectMultipleField):
    '''Custom multiple select that displays a list of checkboxes

    We have a custom pre_validate to handle cases where a
    user has choices from multiple categories. This will insert
    those selected choices into the CHOICES on the class, allowing
    the validation to pass.
    '''
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

    def pre_validate(self, form):
        pass

def validate_phone_number(form, field):
    '''Strips out non-integer characters, checks that it is 10-digits
    '''
    if field.data:
        value = re.sub(ALL_INTEGERS, '', field.data)
        if len(value) != 10 and len(value) != 0:
            raise ValidationError('Invalid 10-digit phone number!')

class SignupForm(Form):
    business_name = fields.TextField(validators=[DataRequired()])
    email = fields.TextField(validators=[DataRequired(), Email()])
    first_name = fields.TextField()
    last_name = fields.TextField()
    phone_number = fields.TextField(validators=[validate_phone_number])
    fax_number = fields.TextField(validators=[validate_phone_number])
    woman_owned = fields.BooleanField('Woman-owned business')
    minority_owned = fields.BooleanField('Minority-owned business')
    veteran_owned = fields.BooleanField('Veteran-owned business')
    disadvantaged_owned = fields.BooleanField('Disadvantaged business enterprise')
    categories = fields.SelectField()
    subcategories = MultiCheckboxField(coerce=int)

    def validate_subcategories(form, field):
        if field.data:
            if len(field.data) == 0:
                raise ValidationError('You must select at least one category!')
            for val in field.data:
                _cat = Category.query.get(val)
                if _cat is None:
                    raise ValidationError('{} is not a valid choice!'.format(val))

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
            if domain != current_app.config.get('CITY_DOMAIN'):
                raise ValidationError("That's not a valid contact!")

def max_words(max=500):
    message = 'Text cannot be more than {} words! You had {} words.'

    def _max_words(form, field):
        l = field.data and len(field.data.split()) or 0
        if l > max:
            raise ValidationError(message.format(max, l))

    return _max_words

def after_today(form, field):

    if isinstance(field.data, datetime.datetime):
        to_test = field.data.date()
    elif isinstance(field.data, datetime.date):
        to_test = field.data
    else:
        raise ValidationError('This must be a date')

    if to_test <= datetime.date.today():
        raise ValidationError('The deadline has to be after today!')

class UnsubscribeForm(Form):
    email = fields.TextField(validators=[DataRequired(), Email(), email_present])
    subscriptions = MultiCheckboxField(coerce=int)

class OpportunityForm(Form):
    department = fields.SelectField(choices=DEPARTMENT_CHOICES, validators=[DataRequired()])
    contact_email = fields.TextField(validators=[Email(), city_domain_email, DataRequired()])
    title = fields.TextField(validators=[DataRequired()])
    description = fields.TextAreaField(validators=[max_words(), DataRequired()])
    planned_open = fields.DateField(validators=[DataRequired()])
    planned_deadline = fields.DateField(validators=[DataRequired(), after_today])
    documents_needed = fields.SelectMultipleField(coerce=int)
    is_public = fields.BooleanField()
    document = FileField(
        validators=[FileAllowed(['pdf'], '.pdf documents only!')]
    )
