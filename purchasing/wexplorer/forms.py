# -*- coding: utf-8 -*-

from flask_wtf import Form

from wtforms.fields import TextField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from purchasing.data.models import ContractType

class SearchForm(Form):
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
        allow_blank=True, blank_text='-----'
    )

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

class FeedbackForm(Form):
    sender = TextField(validators=[Email()], default='No email provided')
    body = TextAreaField(validators=[DataRequired()])

class NoteForm(Form):
    note = TextAreaField(validators=[DataRequired()])
    user = IntegerField(validators=[DataRequired(), NumberRange(min=0)])
