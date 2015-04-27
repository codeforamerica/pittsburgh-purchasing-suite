from flask import url_for, request

from purchasing.extensions import admin, db
from purchasing.decorators import AuthMixin, SuperAdminMixin
from flask_admin.contrib import sqla
from flask_login import current_user
from purchasing.data.models import (
    Stage, StageProperty, Flow, ContractBase, ContractProperty, Company
)
from purchasing.extensions import login_manager
from purchasing.users.models import User, Role

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

class StageAdmin(AuthMixin, sqla.ModelView):
    inline_models = (StageProperty, )

    form_columns = ['name', 'stage_properties']

class ContractAdmin(AuthMixin, sqla.ModelView):
    inline_models = (ContractProperty, Company)

    form_columns = ['contract_type', 'description', 'contract_properties', 'current_stage', 'current_flow']

class CompanyAdmin(AuthMixin, sqla.ModelView):
    inline_models = (ContractBase,)

class FlowAdmin(AuthMixin, sqla.ModelView):
    form_columns = ['flow_name', 'stage_order']

class UserAdmin(AuthMixin, sqla.ModelView):
    form_columns = ['email', 'first_name', 'last_name']

    def is_accessible(self):
        if current_user.is_anonymous():
            return url_for('users.login', next=request.url)
        if current_user.role.name == 'admin':
            return True

class UserRoleAdmin(SuperAdminMixin, sqla.ModelView):
    form_columns = ['email', 'first_name', 'last_name', 'role']

class RoleAdmin(SuperAdminMixin, sqla.ModelView):
    pass

admin.add_view(ContractAdmin(ContractBase, db.session))
admin.add_view(CompanyAdmin(Company, db.session))
admin.add_view(StageAdmin(Stage, db.session))
admin.add_view(FlowAdmin(Flow, db.session))
admin.add_view(UserAdmin(User, db.session, name='User', endpoint='user'))
admin.add_view(UserRoleAdmin(User, db.session, name='User w/Roles', endpoint='user-roles'))
admin.add_view(RoleAdmin(Role, db.session))
