# -*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms.fields import TextField, TextAreaField, SelectMultipleField, BooleanField
from wtforms.validators import DataRequired, Email

class SearchForm(Form):
    q = TextField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

class FilterForm(Form):
    tsv_company_name = BooleanField()
    tsv_contract_description = BooleanField()
    tsv_contract_detail = BooleanField()
    tsv_line_item = BooleanField()
    financial_id = BooleanField()

class FeedbackForm(Form):
    sender = TextField(validators=[Email()], default='No email provided')
    body = TextAreaField(validators=[DataRequired()])
