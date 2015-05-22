# -*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms.fields import TextField
from wtforms.validators import DataRequired

class SearchForm(Form):
    q = TextField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
