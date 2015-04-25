from wtforms import FieldList, IntegerField, TextField, Form
from purchasing.extensions import admin, db
from flask_admin.contrib import sqla
from purchasing.data.models import (
    Stage, StageProperty, Flow, ContractBase, ContractProperty, Company
)
from purchasing.extensions import login_manager
from purchasing.users.models import User, Role

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

class StageAdmin(sqla.ModelView):
    inline_models = (StageProperty, )

    form_columns = ['name', 'stage_properties']

class ContractAdmin(sqla.ModelView):
    inline_models = (ContractProperty, Company)

    form_columns = ['contract_type', 'description', 'contract_properties', 'current_stage', 'current_flow']

class CompanyAdmin(sqla.ModelView):
    inline_models = (ContractBase,)

class FlowAdmin(sqla.ModelView):
    form_columns = ['flow_name', 'stage_order']

class UserAdmin(sqla.ModelView):
    inline_models = (Role,)

admin.add_view(ContractAdmin(ContractBase, db.session))
admin.add_view(CompanyAdmin(Company, db.session))
admin.add_view(StageAdmin(Stage, db.session))
admin.add_view(FlowAdmin(Flow, db.session))
admin.add_view(UserAdmin(User, db.session))
