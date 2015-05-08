# -*- coding: utf-8 -*-
from flask import url_for, request

from wtforms.fields import SelectField
from purchasing.extensions import admin, db
from purchasing.decorators import AuthMixin, SuperAdminMixin
from flask_admin.contrib import sqla
from flask_login import current_user
from purchasing.data.models import (
    Stage, StageProperty, Flow, ContractBase, ContractProperty,
    Company, CompanyContact
)
from purchasing.extensions import login_manager
from purchasing.users.models import User, Role, DEPARTMENT_CHOICES

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

class StageAdmin(AuthMixin, sqla.ModelView):
    inline_models = (StageProperty, )

    form_columns = ['name']

class ContractAdmin(AuthMixin, sqla.ModelView):
    inline_models = (ContractProperty,)

    column_searchable_list = ('description', 'contract_type')

    form_columns = [
        'contract_type', 'description', 'properties',
        'expiration_date', 'current_stage', 'current_flow', 'companies',
        'users'
    ]

class CompanyAdmin(AuthMixin, sqla.ModelView):
    inline_models = (CompanyContact,)

    column_searchable_list = ('company_name',)

    form_columns = [
        'company_name', 'contracts'
    ]

class FlowAdmin(AuthMixin, sqla.ModelView):
    form_columns = ['flow_name', 'stage_order']

class UserAdmin(AuthMixin, sqla.ModelView):
    form_columns = ['email', 'first_name', 'last_name', 'department']

    form_overrides = dict(department=SelectField)
    form_args = dict(department={
        'choices': DEPARTMENT_CHOICES
    })

    def is_accessible(self):
        if current_user.is_anonymous():
            return url_for('users.login', next=request.path)
        if current_user.role.name == 'admin':
            return True

class UserRoleAdmin(SuperAdminMixin, sqla.ModelView):
    form_columns = ['email', 'first_name', 'last_name', 'department', 'role']

class RoleAdmin(SuperAdminMixin, sqla.ModelView):
    pass

admin.add_view(ContractAdmin(ContractBase, db.session, endpoint='contract'))
admin.add_view(CompanyAdmin(Company, db.session, endpoint='company'))
admin.add_view(StageAdmin(Stage, db.session, endpoint='stage'))
admin.add_view(FlowAdmin(Flow, db.session, endpoint='flow'))
admin.add_view(UserAdmin(User, db.session, name='User', endpoint='user'))
admin.add_view(UserRoleAdmin(User, db.session, name='User w/Roles', endpoint='user-roles'))
admin.add_view(RoleAdmin(Role, db.session, endpoint='role'))
