# -*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms.fields import TextField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange

class SearchForm(Form):
    q = TextField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

class FilterForm(Form):
    company_name = BooleanField()
    contract_description = BooleanField()
    contract_detail = BooleanField()
    line_item = BooleanField()
    financial_id = BooleanField()
    archived = BooleanField()

class FeedbackForm(Form):
    sender = TextField(validators=[Email()], default='No email provided')
    body = TextAreaField(validators=[DataRequired()])

class NoteForm(Form):
    note = TextAreaField(validators=[DataRequired()])
    user = IntegerField(validators=[DataRequired(), NumberRange(min=0)])
