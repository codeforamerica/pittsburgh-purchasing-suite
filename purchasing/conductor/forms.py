# -*- coding: utf-8 -*-

import datetime

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import Form as NoCSRFForm
from wtforms.fields import (
    TextField, IntegerField, DateField, TextAreaField, HiddenField,
    FieldList, FormField, SelectField, BooleanField
)
from wtforms.ext.dateutil.fields import DateTimeField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, URL, Optional, Email, Length, Regexp, ValidationError

from purchasing.filters import better_title

from purchasing.users.models import Department, User
from purchasing.data.flows import Flow
from purchasing.data.companies import get_all_companies_query

from purchasing.opportunities.forms import OpportunityForm, city_domain_email

from purchasing.utils import RequiredIf, RequiredOne, RequiredNotBoth
from purchasing.conductor.validators import (
    validate_date, validate_integer, not_all_hidden, get_default,
    validate_multiple_emails, STATE_ABBREV, US_PHONE_REGEX, validate_different,
    validate_unique_name
)

class DynamicStageSelectField(SelectField):
    '''Custom dynamic select field
    '''
    def pre_validate(self, form):
        '''
        '''
        if len(self.data) == 0:
            raise ValidationError('You must select at least one!')
            return False
        return True

class FlowForm(Form):
    id = HiddenField()
    flow_name = TextField(validators=[DataRequired(), validate_unique_name])
    is_archived = BooleanField()

class NewFlowForm(Form):
    flow_name = TextField(validators=[DataRequired(), validate_unique_name])
    stage_order = FieldList(
        DynamicStageSelectField(), min_entries=1,
        validators=[validate_different]
    )

    def __init__(self, stages=[], *args, **kwargs):
        super(NewFlowForm, self).__init__(*args, **kwargs)
        self.stages = stages
        for i in self.stage_order.entries:
            i.choices = self.stages

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
        query_factory=Flow.nonarchived_query_factory,
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
    '''Post opportunities to Beacon
    '''
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
