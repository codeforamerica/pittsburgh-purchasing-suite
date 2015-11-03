# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import TextField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from purchasing.users.models import Department

class DepartmentForm(Form):
    '''Allows user to update profile information

    :var department: sets user department based on choice of available
        departments or none value
    :var first_name: sets first_name value based on user input
    :var last_name: sets last_name value based on user input
    '''
    department = QuerySelectField(
        query_factory=Department.query_factory,
        get_pk=lambda i: i.id,
        get_label=lambda i: i.name,
        allow_blank=True, blank_text='-----'
    )
    first_name = TextField()
    last_name = TextField()
