# -*- coding: utf-8 -*-

import re
import datetime
import pytz

from flask import current_app
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import Form as NoCSRFForm
from wtforms.fields import (
    TextField, IntegerField, DateField, TextAreaField, HiddenField,
    FieldList, FormField, SelectField
)
from wtforms.ext.dateutil.fields import DateTimeField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, URL, Optional, ValidationError, Email, Length, Regexp

from purchasing.filters import better_title

from purchasing.users.models import Department, User
from purchasing.data.flows import Flow
from purchasing.data.companies import get_all_companies_query
from purchasing.data.contracts import ContractType

from purchasing.opportunities.forms import OpportunityForm, city_domain_email
from purchasing.utils import RequiredIf, RequiredOne, RequiredNotBoth

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

class CompleteForm(Form):
    complete = DateTimeField(
        validators=[validate_date]
    )

    def __init__(self, started=None, *args, **kwargs):
        super(CompleteForm, self).__init__(*args, **kwargs)
        self.started = started.replace(second=0, microsecond=0) if started else None
        self.maximum = datetime.datetime.utcnow()

class NewContractForm(Form):
    description = TextField(validators=[DataRequired()])
    flow = QuerySelectField(
        query_factory=Flow.all_flow_query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.flow_name,
        allow_blank=True, blank_text='-----'
    )
    assigned = QuerySelectField(
        query_factory=User.conductor_users_query,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.email,
        allow_blank=True, blank_text='-----'
    )
    department = QuerySelectField(
        query_factory=Department.query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )
    start = DateTimeField(default=get_default)

class EditContractForm(Form):
    '''Form to control details needed to finalize a new/renewed contract
    '''
    description = TextField(validators=[DataRequired()])
    expiration_date = DateField(validators=[DataRequired()])
    spec_number = TextField(validators=[DataRequired()])
    contract_href = TextField(validators=[Optional(), URL(message="That URL doesn't work!")])

class ContractMetadataForm(Form):
    '''Edit a contract's metadata during the renewal process
    '''
    financial_id = IntegerField(validators=[Optional()])
    spec_number = TextField(validators=[Optional()], filters=[lambda x: x or None])
    all_blank = HiddenField(validators=[not_all_hidden])
    department = QuerySelectField(
        query_factory=Department.query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )

class AttachmentForm(Form):
    upload = FileField('datafile', validators=[
        FileAllowed(['doc', 'docx', 'xls', 'xlsx', 'pdf'], message='Invalid file type')
    ])

class SendUpdateForm(Form):
    '''Form to update
    '''
    send_to = TextField(validators=[DataRequired(), validate_multiple_emails])
    send_to_cc = TextField(validators=[Optional(), validate_multiple_emails])
    subject = TextField(validators=[DataRequired()])
    body = TextAreaField(validators=[DataRequired()])
    attachments = FieldList(FormField(AttachmentForm), min_entries=1)

class PostOpportunityForm(OpportunityForm):
    contact_email = TextField(validators=[Email(), city_domain_email, Optional()])

class NoteForm(Form):
    '''Adds a note to the contract stage view
    '''
    note = TextAreaField(validators=[DataRequired(message='Note cannot be blank.')])

class FileUploadForm(Form):
    upload = FileField('datafile', validators=[
        FileAllowed(['csv'], message='.csv files only')
    ])

class ContractUploadForm(Form):
    contract_id = HiddenField('id', validators=[DataRequired()])
    upload = FileField('datafile', validators=[
        FileRequired(),
        FileAllowed(['pdf'], message='.pdf files only')
    ])

class CompanyContactForm(NoCSRFForm):
    first_name = TextField(validators=[DataRequired()])
    last_name = TextField(validators=[DataRequired()])
    addr1 = TextField(validators=[Optional()])
    addr2 = TextField(validators=[Optional()])
    city = TextField(validators=[Optional()])
    state = SelectField(validators=[Optional(), RequiredIf('city')], choices=[('', '---')] +
        [(state, state) for state in STATE_ABBREV]
    )
    zip_code = TextField(
        validators=[
            validate_integer, Optional(),
            RequiredIf('city'), Length(min=5, max=5, message='Field must be 5 characters long.')
        ]
    )
    phone_number = TextField(validators=[DataRequired(), Regexp(
        US_PHONE_REGEX, message='Please enter numbers in XXX-XXX-XXXX format'
    )])
    fax_number = TextField(validators=[Optional(), Regexp(
        US_PHONE_REGEX, message='Please enter numbers in XXX-XXX-XXXX format'
    )])
    email = TextField(validators=[Email(), DataRequired()])

class CompanyForm(NoCSRFForm):
    new_company_controller_number = TextField('New Company Controller Number', validators=[
        RequiredOne('controller_number'),
        RequiredNotBoth('controller_number'), RequiredIf('new_company_name'),
        validate_integer
    ])
    new_company_name = TextField('New Company Name', validators=[
        RequiredOne('company_name'),
        RequiredNotBoth('company_name'), RequiredIf('new_company_controller_number'),
    ])

    controller_number = TextField('Existing Company Controller Number', validators=[
        RequiredOne('new_company_controller_number'),
        RequiredNotBoth('new_company_controller_number'),
        RequiredIf('company_name'), validate_integer
    ])
    company_name = QuerySelectField(
        'Existing Company Name', query_factory=get_all_companies_query, get_pk=lambda i: i.id,
        get_label=lambda i: better_title(i.company_name),
        allow_blank=True, blank_text='-----',
        validators=[
            RequiredOne('new_company_name'),
            RequiredNotBoth('new_company_name'), RequiredIf('controller_number'),
       ]
    )

class CompanyListForm(Form):
    companies = FieldList(FormField(CompanyForm), min_entries=1)

class CompanyContactList(NoCSRFForm):
    contacts = FieldList(FormField(CompanyContactForm), min_entries=1)

class CompanyContactListForm(Form):
    companies = FieldList(FormField(CompanyContactList), min_entries=0)
