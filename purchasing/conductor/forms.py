# -*- coding: utf-8 -*-

import re
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms.fields import (
    TextField, IntegerField, DateField, TextAreaField, HiddenField,
    FieldList, FormField, SelectField
)
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import (
    DataRequired, URL, Optional, ValidationError, Email
)

from purchasing.filters import better_title

from purchasing.users.models import department_query
from purchasing.data.models import Company
from purchasing.data.companies import get_all_companies_query

from purchasing.opportunities.forms import OpportunityForm
from purchasing.utils import RequiredIf, RequiredOne, RequiredNotBoth

EMAIL_REGEX = re.compile(r'^.+@([^.@][^@]+)$', re.IGNORECASE)

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

class EditContractForm(Form):
    '''Form to control details needed to finalize a new/renewed contract
    '''

    description = TextField(validators=[DataRequired()])
    financial_id = IntegerField(validators=[DataRequired(message="A number is required.")])
    expiration_date = DateField(validators=[DataRequired()])
    spec_number = TextField(validators=[DataRequired()])
    contract_href = TextField(validators=[Optional(), URL(message="That URL doesn't work!")])

class ContractMetadataForm(Form):
    '''Edit a contract's metadata during the renewal process
    '''
    financial_id = IntegerField(validators=[Optional()])
    expiration_date = DateField(validators=[Optional()])
    spec_number = TextField(validators=[Optional()], filters=[lambda x: x or None])
    all_blank = HiddenField(validators=[not_all_hidden])
    department = QuerySelectField(
        query_factory=department_query,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )

class SendUpdateForm(Form):
    '''Form to update
    '''
    send_to = TextField(validators=[DataRequired(), validate_multiple_emails])
    send_to_cc = TextField(validators=[Optional(), validate_multiple_emails])
    subject = TextField(validators=[DataRequired()])
    body = TextAreaField(validators=[DataRequired()])

class PostOpportunityForm(OpportunityForm):
    pass

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
        FileAllowed(['pdf'], message='.pdf files only')
    ])

class CompanyContactForm(Form):
    company_name = HiddenField()
    first_name = TextField(validators=[DataRequired()])
    last_name = TextField(validators=[DataRequired()])
    addr1 = TextField(validators=[DataRequired()])
    addr2 = TextField()
    city = TextField(validators=[DataRequired()])
    state = TextField(validators=[DataRequired()])
    zip_code = IntegerField(validators=[DataRequired()])
    phone_number = IntegerField(validators=[DataRequired()])
    fax_number = IntegerField()
    email = TextField(validators=[Email(), DataRequired()])

def validate_integer(form, field):
    if field.data:
        try:
            int(field.data)
        except:
            raise ValidationError('This must be an integer!')

class CompanyForm(Form):
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

class CompanyContactList(Form):
    contacts = FieldList(FormField(CompanyContactForm), min_entries=1)

class CompanyContactListForm(Form):
    companies = FieldList(FormField(CompanyContactList))
