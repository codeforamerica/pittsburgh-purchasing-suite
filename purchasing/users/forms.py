# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import TextField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from purchasing.users.models import department_query

class DepartmentForm(Form):
    department = QuerySelectField(
        query_factory=department_query,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )
    first_name = TextField()
    last_name = TextField()
