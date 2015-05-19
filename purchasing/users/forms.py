# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import SelectField, TextField
from purchasing.users.models import DEPARTMENT_CHOICES

class DepartmentForm(Form):
    department = SelectField(choices=DEPARTMENT_CHOICES)
    first_name = TextField()
    last_name = TextField()
