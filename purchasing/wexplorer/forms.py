# -*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms.fields import TextField, SelectField
from wtforms.validators import DataRequired
from purchasing.users.models import DEPARTMENT_CHOICES

class SearchForm(Form):
    q = TextField('Search', validators=[DataRequired()])
    department = SelectField(choices=DEPARTMENT_CHOICES)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
