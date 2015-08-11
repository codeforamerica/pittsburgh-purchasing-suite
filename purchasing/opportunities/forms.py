# -*- coding: utf-8 -*-

import re
import datetime

from flask import current_app
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import widgets, fields
from wtforms.validators import (
    DataRequired, Email, ValidationError, Optional, InputRequired
)

from purchasing.opportunities.models import Vendor

from purchasing.users.models import DEPARTMENT_CHOICES, User

ALL_INTEGERS = re.compile('[^\d.]')
DOMAINS = re.compile('@[\w.]+')

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
            raise Exception('no field named "%s" in form' % self.other_field_name)
            if bool(other_field.data):
                super(RequiredIf, self).__call__(form, field)

def build_label_tooltip(name, description, href):
    return '''
    {} <i
        class="fa fa-question-circle"
        aria-hidden="true" data-toggle="tooltip"
        data-placement="right" title="{}">
    </i>'''.format(name, description)

def select_multi_checkbox(field, ul_class='', **kwargs):
    '''Custom multi-select widget for vendor documents needed

    Renders with tooltips describing each document
    '''
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<div %s>' % widgets.html_params(id=field_id, class_=ul_class)]
    for value, label, checked in field.iter_choices():
        name, description, href = label
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'<div class="checkbox">')
        html.append(u'<input %s /> ' % widgets.html_params(**options))
        html.append(u'<label for="%s">%s</label>' % (choice_id, build_label_tooltip(name, description, href)))
        html.append(u'</div>')
    html.append(u'</div>')
    return u''.join(html)

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

class VendorSignupForm(SignupForm):
    first_name = fields.TextField()
    last_name = fields.TextField()
    phone_number = fields.TextField(validators=[validate_phone_number])
    fax_number = fields.TextField(validators=[validate_phone_number])
    woman_owned = fields.BooleanField('Woman-owned business')
    minority_owned = fields.BooleanField('Minority-owned business')
    veteran_owned = fields.BooleanField('Veteran-owned business')
    disadvantaged_owned = fields.BooleanField('Disadvantaged business enterprise')
    subcategories = MultiCheckboxField(coerce=int, choices=[])
    categories = fields.SelectField(choices=[], validators=[])

class OpportunitySignupForm(SignupForm):
    subcategories = MultiCheckboxField(coerce=int, choices=[])
    categories = fields.SelectField(choices=[], validators=[Optional()])
    also_categories = fields.BooleanField()

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
            if domain.group().lstrip('@') != current_app.config.get('CITY_DOMAIN'):
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
    categories = MultiCheckboxField(coerce=int)
    opportunities = MultiCheckboxField(coerce=int)

class OpportunityDocumentForm(Form):
    title = fields.TextField(validators=[RequiredIf('document')])
    document = FileField(
        validators=[FileAllowed(
            ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
            '.pdf, Word (.doc/.docx), and Excel (.xls/.xlsx) documents only!')
        ]
    )

class OpportunityForm(Form):
    department = fields.SelectField(choices=DEPARTMENT_CHOICES, validators=[DataRequired()])
    contact_email = fields.TextField(validators=[Email(), city_domain_email, DataRequired()])
    title = fields.TextField(validators=[DataRequired()])
    description = fields.TextAreaField(validators=[max_words(), DataRequired()])
    planned_advertise = fields.DateField(validators=[DataRequired()])
    planned_open = fields.DateField(validators=[DataRequired()])
    planned_deadline = fields.DateField(validators=[DataRequired(), after_today])
    vendor_documents_needed = fields.SelectMultipleField(widget=select_multi_checkbox, coerce=int)
    categories = fields.SelectField(choices=[], validators=[Optional()])
    subcategories = MultiCheckboxField(coerce=int, validators=[Optional()], choices=[])
    documents = fields.FieldList(fields.FormField(OpportunityDocumentForm), min_entries=1)
