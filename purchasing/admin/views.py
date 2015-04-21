from purchasing.extensions import admin, db
from flask_admin.contrib import sqla
from purchasing.data.models import (
    Stage, StageProperty, Flow, ContractBase, ContractProperty
)

class StageAdmin(sqla.ModelView):
    inline_models = (StageProperty, )

    form_columns = ['name', 'stage_property']

class ContractAdmin(sqla.ModelView):
    inline_models = (ContractProperty,)

    form_columns = ['contract_type', 'description', 'contract_properties']

admin.add_view(ContractAdmin(ContractBase, db.session))
admin.add_view(StageAdmin(Stage, db.session))
admin.add_view(sqla.ModelView(Flow, db.session))
