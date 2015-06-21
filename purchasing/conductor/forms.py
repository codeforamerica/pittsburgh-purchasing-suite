# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import TextField, IntegerField, DateField
from wtforms.validators import DataRequired, URL

class EditContractForm(Form):
    '''Form to control details needed for new contract
    '''

    description = TextField(validators=[DataRequired()])
    financial_id = IntegerField(validators=[DataRequired(message="A number is required.")])
    expiration_date = DateField(validators=[DataRequired()])
    spec_number = TextField(validators=[DataRequired()])
    contract_href = TextField(validators=[DataRequired(), URL()])
