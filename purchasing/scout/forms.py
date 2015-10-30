# -*- coding: utf-8 -*-

from flask_wtf import Form

from wtforms.fields import TextField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from purchasing.data.contracts import ContractType

class SearchForm(Form):
    '''Form to handle Scout search and filter
    '''
    q = TextField('Search', validators=[DataRequired()])
    company_name = BooleanField()
    contract_description = BooleanField()
    contract_detail = BooleanField()
    line_item = BooleanField()
    financial_id = BooleanField()
    archived = BooleanField()
    contract_type = QuerySelectField(
        query_factory=ContractType.query_factory_all,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='Choose type of contract'
    )

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

class FeedbackForm(Form):
    '''Form to collect sender and body for Scout contract feedback
    '''
    sender = TextField(validators=[Email()], default='No email provided')
    body = TextAreaField(validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(FeedbackForm, self).__init__(*args, **kwargs)


class NoteForm(Form):
    '''Form to allow users to write notes about contracts
    '''
    note = TextAreaField(validators=[DataRequired()])
    user = IntegerField(validators=[DataRequired(), NumberRange(min=0)])

    def __init__(self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)
