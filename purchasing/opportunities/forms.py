# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import BooleanField, TextField, SelectField
from wtforms.validators import DataRequired, Email

class SignupForm(Form):
    business_name = TextField(validators=[DataRequired(), ])
    email = TextField(validators=[DataRequired(), Email()])
    first_name = TextField()
    last_name = TextField()
    phone_number = TextField()
    fax_number = TextField()
    minority_owned = BooleanField()
    veteran_owned = BooleanField()
    women_owned = BooleanField()
    disadvantaged_owned = BooleanField()
