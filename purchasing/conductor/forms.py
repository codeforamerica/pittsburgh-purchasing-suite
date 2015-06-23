# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import TextField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, URL, Email

class EditContractForm(Form):
    '''Form to control details needed for new contract
    '''

    description = TextField(validators=[DataRequired()])
    financial_id = IntegerField(validators=[DataRequired(message="A number is required.")])
    expiration_date = DateField(validators=[DataRequired()])
    spec_number = TextField(validators=[DataRequired()])
    contract_href = TextField(validators=[DataRequired(), URL()])

class SendUpdateForm(Form):
    '''Form to update
    '''
    send_to = TextField(validators=[DataRequired(), Email()])
    subject = TextField(validators=[DataRequired()])
    body = TextAreaField(validators=[DataRequired()])

class PostOpportunityForm(Form):
    '''
    '''
    pass

class NoteForm(Form):
    '''Adds a note to the contract stage view
    '''
    note = TextAreaField(validators=[DataRequired(message='Note cannot be blank.')])
