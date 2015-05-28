# -*- coding: utf-8 -*-

import re

from flask_wtf import Form
from wtforms import widgets, fields
from wtforms.validators import DataRequired, Email, ValidationError

ALL_INTEGERS = re.compile('[^\d.]')

class MultiCheckboxField(fields.SelectMultipleField):
    '''
    Custom multiple select that displays a list of checkboxes
    '''
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

def validate_phone_number(form, field):
    '''
    Strips out non-integer characters, checks that it is 10-digits
    '''
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
    categories = fields.SelectField(validators=[DataRequired()])
    subcategories = MultiCheckboxField(validators=[DataRequired()])
