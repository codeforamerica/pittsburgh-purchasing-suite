# -*- coding: utf-8 -*-

import datetime

from flask import current_app

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_login import current_user
from wtforms import Form as NoCSRFForm
from wtforms.fields import (
    TextField, IntegerField, DateField, TextAreaField, HiddenField,
    FieldList, FormField, SelectField, BooleanField
)
from wtforms.ext.dateutil.fields import DateTimeField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, URL, Optional, Email, Length, Regexp, ValidationError

from purchasing.database import db
from purchasing.filters import better_title
from purchasing.notifications import Notification

from purchasing.users.models import Department, User
from purchasing.data.flows import Flow
from purchasing.data.companies import Company

from purchasing.opportunities.forms import OpportunityForm, city_domain_email
from purchasing.opportunities.models import Opportunity

from purchasing.utils import RequiredIf, RequiredOne, RequiredNotBoth
from purchasing.conductor.validators import (
    validate_date, validate_integer, not_all_hidden, get_default,
    validate_multiple_emails, STATE_ABBREV, US_PHONE_REGEX, validate_different,
    validate_unique_name
)

class DynamicStageSelectField(SelectField):
    '''Select field to allow dynamic choice construction
    '''
    def pre_validate(self, form):
        '''Raise an error if there is nothing in the data, otherwise return true
        '''
        if len(self.data) == 0:
            raise ValidationError('You must select at least one!')
            return False
        return True

class FlowForm(Form):
    '''Form for editing existing form metadata

    Attributes:
        id: Hidden field to hold the form's ID
        flow_name: Name of the flow
        is_archived: Whether or not the flow is archived
    '''
    id = HiddenField()
    flow_name = TextField(validators=[DataRequired(), validate_unique_name])
    is_archived = BooleanField()

class NewFlowForm(Form):
    '''Form for creating new flows

    Attributes:
        flow_name: Name of the flow
        stage_order: A list of
            :py:class:`~purchasing.conductor.forms.DynamicStageSelectField`
            fields that represent different stages

    Arguments:
        stages: A list of (id, name) values used to build choices
        *args: List of arguments passed to the form's superclass
        **kwargs: List of keyword arguments passed to the form's
            superclass
    '''
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
    '''Form to hold the completion times

    Attributes:
        complete: Field to hold the date/time for when to complete
            a certain :py:class:`~purchasing.data.contract_stages.ContractStage`
        maximum: (instance variable) The current utc time

    Arguments:
        started: Datetime of what the minimum time should be,
            such as when the
            :py:class:`~purchasing.data.contract_stages.ContractStage`
            started. Because the ``complete`` form attribute uses the
            :py:func:`~purchasing.conductor.validators.validate_date`
            validator, passing a minumim is important to ensure the validator
            works properly (if you want to make sure that
            :py:class:`~purchasing.data.contract_stages.ContractStage`
            objects don't end before they start. Optional to allow the first
            stage in a give :py:class:`~purchasing.data.flows.Flow` to start
            in the past.
    '''
    complete = DateTimeField(
        validators=[validate_date]
    )

    def __init__(self, started=None, *args, **kwargs):
        super(CompleteForm, self).__init__(*args, **kwargs)
        self.started = started.replace(second=0, microsecond=0) if started else None
        self.maximum = datetime.datetime.utcnow()

class NewContractForm(Form):
    '''Form for starting new work on a contract through conductor

    Attributes:
        description: The contract's description
        flow: The :py:class:`~purchasing.data.flows.Flow` the
            contract should follow
        assigned: The :py:class:`~purchasing.users.models.User`
            the contract should be assigned to
        department: The :py:class:`~purchasing.users.models.Department`
            the contract should be assigned to
        start: The start time for the first
            :py:class:`~purchasing.data.contract_stages.ContractStage`
            for the contract
    '''
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

class ContractMetadataForm(Form):
    '''Edit a contract's metadata during the renewal process

    Attributes:
        financial_id: The
            :py:class:`~purchasing.data.contracts.ContractBase`
            financial_id
        spec_number: The spec number for a contrat. See
            :py:meth:`~purchasing.data.contracts.ContractBase.get_spec_number`
            for more information about spec numbers
        department: The :py:class:`~purchasing.users.models.Department` to set
            for the contract
        all_blank: Placeholder to indicate if all other fields are blank
    '''
    financial_id = IntegerField(validators=[Optional()])
    spec_number = TextField(validators=[Optional()], filters=[lambda x: x or None])
    department = QuerySelectField(
        query_factory=Department.query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )
    all_blank = HiddenField(validators=[not_all_hidden])

    def post_validate_action(self, action, contract, current_stage):
        '''Update the contract's metadata

        Arguments:
            action: A
                :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
                that needs to be updated with details for the action
                log
            contract: A :py:class:`~purchasing.data.contracts.ContractBase` object
            current_stage: The current
                :py:class:`~purchasing.data.contract_stages.ContractStage`

        Returns:
            The modified
            :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            with the action detail updated to include the form's data
        '''
        current_app.logger.info(
            'CONDUCTOR UPDATE METADATA | Contract update metadata on stage "{}" from contract "{}" (ID: {})'.format(
                current_stage.name, contract.description, contract.id
            )
        )

        # remove the blank hidden field -- we don't need it
        data = self.data
        del data['all_blank']

        contract.update_with_spec_number(data)
        # this process pops off the spec number, so get it back
        data['spec_number'] = self.data.get('spec_number')

        # get department
        if self.data.get('department', None):
            data['department'] = self.data.get('department').name

        action.action_detail = data

        return action

class AttachmentForm(NoCSRFForm):
    '''Form to hold individual attachments for email updates

    Wrapped in a list by :py:class:`~purchasing.conductor.forms.SendUpdateForm`

    Attributes:
        upload: File field which holds an uploaded file. Must be a Word,
            Excel, or .pdf document
    '''
    upload = FileField('datafile', validators=[
        FileAllowed(['doc', 'docx', 'xls', 'xlsx', 'pdf'], message='Invalid file type')
    ])

class SendUpdateForm(Form):
    '''Form to send an email update

    Attributes:
        send_to: Email or semicolon-delimited list of email addresses
            to send the update email to
        send_to_cc: Email or semicolon-delimited list of email
            addresses to cc on the update
        subject: The subject the update should have
        body: The body of the message the subject should have. This
            can be configured as a property of a
            :py:class:`~purchasing.data.stages.Stage`
        attachments: A list of files. Wraps
            :py:class:`~purchasing.conductor.forms.AttachmentForm`
    '''
    send_to = TextField(validators=[DataRequired(), validate_multiple_emails])
    send_to_cc = TextField(validators=[Optional(), validate_multiple_emails])
    subject = TextField(validators=[DataRequired()])
    body = TextAreaField(validators=[DataRequired()])
    attachments = FieldList(FormField(AttachmentForm), min_entries=1)

    def get_attachment_filenames(self):
        '''Return the names of all of the attached files or None
        '''
        filenames = []
        for attachment in self.attachments.entries:
            try:
                return filenames.append(attachment.upload.data.filename)
            except AttributeError:
                continue
        return filenames if len(filenames) > 0 else None

    def post_validate_action(self, action, contract, current_stage):
        '''Send the email updates

        Arguments:
            action: A
                :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
                that needs to be updated with details for the action
                log
            contract: A :py:class:`~purchasing.data.contracts.ContractBase` object
            current_stage: The current
                :py:class:`~purchasing.data.contract_stages.ContractStage`

        Returns:
            The modified
            :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            with the action detail updated to include the form's data
        '''
        current_app.logger.info(
            'CONDUCTOR EMAIL UPDATE | New update on stage "{}" from contract "{}" (ID: {})'.format(
                current_stage.name, contract.description, contract.id
            )
        )

        action.action_detail = {
            'sent_to': self.data.get('send_to', ''),
            'body': self.data.get('body'),
            'subject': self.data.get('subject'),
            'stage_name': current_stage.name,
            'attachments': self.get_attachment_filenames()
        }

        Notification(
            to_email=[i.strip() for i in self.data.get('send_to').split(';') if i != ''],
            from_email=current_app.config['CONDUCTOR_SENDER'],
            reply_to=current_user.email,
            cc_email=[i.strip() for i in self.data.get('send_to_cc').split(';') if i != ''],
            subject=self.data.get('subject'),
            html_template='conductor/emails/email_update.html',
            body=self.data.get('body'),
            attachments=[i.upload.data for i in self.attachments.entries]
        ).send(multi=False)

        return action

class PostOpportunityForm(OpportunityForm):
    '''Form to post opportunities to Beacon

    Attributes:
        contact_email: Override the base form to make the
            contact email optional for a opportunity posted
            from conductor

    See Also:
        :py:class:`~purchasing.opportunities.forms.OpportunityForm`
    '''
    contact_email = TextField(validators=[Email(), city_domain_email, Optional()])

    def post_validate_action(self, action, contract, current_stage):
        '''Post the opportunity to Beacon

        Arguments:
            action: A
                :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
                that needs to be updated with details for the action
                log
            contract: A :py:class:`~purchasing.data.contracts.ContractBase` object
            current_stage: The current
                :py:class:`~purchasing.data.contract_stages.ContractStage`

        Returns:
            The modified
            :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            with the action detail updated to include the form's data
        '''
        current_app.logger.info(
            'CONDUCTOR BEACON POST | Beacon posting on stage "{}" from contract "{}" (ID: {})'.format(
                current_stage.name, contract.description, contract.id
            )
        )

        opportunity_data = self.data_cleanup()
        opportunity_data['created_from_id'] = contract.id

        if contract.opportunity:
            label = 'updated'
            contract.opportunity.update(
                opportunity_data, current_user,
                self.documents, True
            )
            opportunity = contract.opportunity

        else:
            label = 'created'
            opportunity = Opportunity.create(
                opportunity_data, current_user,
                self.documents, True
            )
            db.session.add(opportunity)
            db.session.commit()

        action.action_detail = {
            'opportunity_id': opportunity.id, 'title': opportunity.title,
            'label': label
        }

        return action

class NoteForm(Form):
    '''Form to take notes

    Attributes:
        note: Text of the note to be taken
    '''
    note = TextAreaField(validators=[DataRequired(message='Note cannot be blank.')])

    def post_validate_action(self, action, contract, current_stage):
        '''Post the note

        Arguments:
            action: A
                :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
                that needs to be updated with details for the action
                log
            contract: A :py:class:`~purchasing.data.contracts.ContractBase` object
            current_stage: The current
                :py:class:`~purchasing.data.contract_stages.ContractStage`

        Returns:
            The modified
            :py:class:`~purchasing.data.contract_stages.ContractStageActionItem`
            with the action detail updated to include the form's data
        '''
        current_app.logger.info(
            'CONDUCTOR NOTE | New note on stage "{}" from contract "{}" (ID: {})'.format(
                current_stage.name, contract.description, contract.id
            )
        )

        action.action_detail = {
            'note': self.data.get('note', ''),
            'stage_name': current_stage.name
        }
        return action

class FileUploadForm(Form):
    '''Form to take new costars data for upload

    Attributes:
        upload: csv file to be uploaded
    '''
    upload = FileField('datafile', validators=[
        FileAllowed(['csv'], message='.csv files only')
    ])

class ContractUploadForm(Form):
    '''Form to upload a pdf for a costars contract

    Attributes:
        contract_id: ID of the contract to be uploaded (hidden field)
        upload: The file to be uploaded
    '''
    contract_id = HiddenField('id', validators=[DataRequired()])
    upload = FileField('datafile', validators=[
        FileRequired(),
        FileAllowed(['pdf'], message='.pdf files only')
    ])

class EditContractForm(Form):
    '''Form to control details needed to finalize a new/renewed contract

    Attributes:
        description: The final description of the contract (required)
        expiration_date: The new expiration date for the new/renewed contract (required)
        spec_number: The county spec number (see
            :py:meth:`~purchasing.data.contracts.ContractBase.get_spec_number`
            , required)
        contract_href: A link to the actual contract document
    '''
    description = TextField(validators=[DataRequired()])
    expiration_date = DateField(validators=[DataRequired()])
    spec_number = TextField(validators=[DataRequired()])
    contract_href = TextField(validators=[Optional(), URL(message="That URL doesn't work!")])

class CompanyContactForm(NoCSRFForm):
    '''Form to capture contact information for a company

    Attributes:
        first_name: First name of the contact
        last_name: Last name of the contact
        addr1: First line of the contact's address
        addr2: Second line of the contract's address
        city: Contact address city
        state: Contact address state
        zip_code: Contact address zip code
        phone_number: Contact phone number
        fax_number: Contact fax number
        email: Contact email

    See Also:
        :py:class:`~purchasing.data.models.companies.CompanyContact`
    '''
    first_name = TextField(validators=[DataRequired()])
    last_name = TextField(validators=[DataRequired()])
    addr1 = TextField(validators=[Optional()])
    addr2 = TextField(validators=[Optional()])
    city = TextField(validators=[Optional()])
    state = SelectField(validators=[Optional(), RequiredIf('city')], choices=[
        ('', '---')] +
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
    '''A form to assign a company to a contract

    This is an individual new/existing company that is part of the
    :py:class:`~purchasing.conductor.forms.CompanyListForm` entries.
    For an individual entry, both the ``new_company_name`` and the
    ``new_company_controller_number`` *or* the ``company_name``
    and the ``controller_number`` must be filled out. Both cannot be
    filled out and they cannot be partially filled out.

    Attributes:
        new_company_controller_number: Controller number for a new company
        new_company_name: Name for a new company
        controller_number: Controller number for an existing company
        company_name: Name of an existing copany, uses a query select field
    '''
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
        'Existing Company Name', query_factory=Company.all_companies_query_factory, get_pk=lambda i: i.id,
        get_label=lambda i: better_title(i.company_name),
        allow_blank=True, blank_text='-----',
        validators=[
            RequiredOne('new_company_name'),
            RequiredNotBoth('new_company_name'),
            RequiredIf('controller_number')
        ]
    )

class CompanyListForm(Form):
    '''Form that holds lists of new/existing companies

    Attributes:
        companies: List of :py:class:`~purchasing.conductor.forms.CompanyForm`
            form fields
    '''
    companies = FieldList(FormField(CompanyForm), min_entries=1)

class CompanyContactList(NoCSRFForm):
    '''Form to hold lists of company contacts

    This form is the inner level of a twice-nested list. On the outer
    level (see :py:class:`~purchasing.conductor.forms.CompanyContactListForm`
    ), we have a list of companies. Each of those companies could have
    multiple contacts, though, so we need an inner nested list to handle
    that. This is that inner portion.

    Attributes:
        contacts: List of :py:class:`~purchasing.conductor.forms.CompanyContactForm`
            form fields
    '''
    contacts = FieldList(FormField(CompanyContactForm), min_entries=1)

class CompanyContactListForm(Form):
    '''Outer form to collect all contacts for all companies for the contract

    Attributes:
        companies: A outer list around the nested
            :py:class:`~purchasing.conductor.forms.CompanyContactList`
    '''
    companies = FieldList(FormField(CompanyContactList), min_entries=0)
