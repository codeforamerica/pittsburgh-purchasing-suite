# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import TextField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from purchasing.users.models import Department

class DepartmentForm(Form):
    department = QuerySelectField(
        query_factory=Department.query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )
    first_name = TextField()
    last_name = TextField()
