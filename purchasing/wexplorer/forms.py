# -*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms.fields import TextField, TextAreaField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired, Email

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

class FeedbackForm(Form):
    sender = TextField(validators=[Email()], default='No email provided')
    body = TextAreaField(validators=[DataRequired()])
