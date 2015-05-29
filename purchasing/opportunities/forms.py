# -*- coding: utf-8 -*-

import re

from flask_wtf import Form
from wtforms import widgets, fields
from wtforms.validators import DataRequired, InputRequired, Email, ValidationError

from purchasing.opportunities.models import Category

ALL_INTEGERS = re.compile('[^\d.]')

class MultiCheckboxField(fields.SelectMultipleField):
    '''
    Custom multiple select that displays a list of checkboxes

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
    '''
    Strips out non-integer characters, checks that it is 10-digits
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
