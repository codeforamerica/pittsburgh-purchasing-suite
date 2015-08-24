# -*- coding: utf-8 -*-

from wtforms.ext.sqlalchemy.fields import QuerySelectField
from purchasing.extensions import admin, db
from purchasing.decorators import AuthMixin, SuperAdminMixin, ConductorAuthMixin
from flask_admin.contrib import sqla
from flask_admin.form.widgets import Select2Widget
from purchasing.data.models import (
    Stage, StageProperty, Flow, ContractBase, ContractProperty,
    Company, CompanyContact, LineItem, company_contract_association_table
)
from purchasing.opportunities.models import RequiredBidDocument
from purchasing.conductor.forms import validate_integer
from purchasing.extensions import login_manager
from purchasing.users.models import User, Role, department_query, role_query
from purchasing.opportunities.models import Opportunity

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

class CompanyAdmin(AuthMixin, sqla.ModelView):
    inline_models = (CompanyContact,)

    column_searchable_list = ('company_name',)

    form_columns = [
        'company_name', 'contracts'
    ]

class ContractBaseAdmin(AuthMixin, sqla.ModelView):
    '''Base model for different representations of contracts
    '''
    edit_template = 'admin/purchasing_edit.html'
    create_template = 'admin/purchasing_create.html'

    column_searchable_list = (
        ContractBase.description, ContractBase.contract_type,
        ContractProperty.value, Company.company_name
    )

    column_list = [
        'contract_type', 'description', 'financial_id', 'expiration_date',
        'properties', 'companies', 'is_archived'
    ]

    column_labels = dict(
        contract_href='Link to Contract PDF', financial_id='Controller #',
        properties='Contract Properties', expiration_date='Expiration', is_archived='Archived'
    )

    form_args = {
        'financial_id': {
            'validators': [validate_integer]
        }
    }

    def init_search(self):
        r = super(ContractBaseAdmin, self).init_search()
        self._search_joins.append(company_contract_association_table)
        self._search_joins.reverse()
        return r

    def scaffold_filters(self, name):
        filters = super(ContractBaseAdmin, self).scaffold_filters(name)
        if 'company_name' in self._filter_joins:
            self._filter_joins['company_name'].append(company_contract_association_table)
            self._filter_joins.reverse()

        return filters

class ScoutContractAdmin(ContractBaseAdmin):
    inline_models = (ContractProperty, LineItem,)

    form_columns = [
        'contract_type', 'description', 'properties',
        'financial_id', 'expiration_date', 'contract_href',
        'companies', 'followers', 'is_archived'
    ]

class ConductorContractAdmin(ContractBaseAdmin):
    inline_models = (ContractProperty,)

    column_list = [
        'description', 'expiration_date', 'current_stage', 'current_flow', 'assigned'
    ]

    form_columns = [
        'contract_type', 'description', 'properties',
        'financial_id', 'expiration_date', 'contract_href',
        'companies', 'followers', 'is_archived', 'assigned'
    ]

    def get_query(self):
        '''Override default get query to limit to assigned contracts
        '''
        return super(ConductorContractAdmin, self).get_query().filter(
            ContractBase.assigned_to != None
        )

    def get_count_query(self):
        '''Override default get count query to conform to above
        '''
        return super(ConductorContractAdmin, self).get_count_query().filter(
            ContractBase.assigned_to != None
        )

    def create_form(self):
        return self._use_filtered_users(super(ContractBaseAdmin, self).create_form())

    def edit_form(self, obj):
        '''Override to only show the correct users in the assigned column
        '''
        return self._use_filtered_users(super(ContractBaseAdmin, self).edit_form(obj))

    def _use_filtered_users(self, form):
        form.assigned.query_factory = self._get_filtered_users
        return form

    def _get_filtered_users(self):
        return self.session.query(User).join(Role).filter(
            Role.name.in_(['conductor', 'admin', 'superadmin'])
        )

def get_stages():
    return Stage.query.order_by(Stage.name)

class QuerySelect2TagsWidget(Select2Widget):
    def __init__(self, *args, **kwargs):
        super(QuerySelect2TagsWidget, self).__init__(*args, **kwargs)

    def __call__(self, field, **kwargs):
        field.data = Stage.query.filter(Stage.id.in_(field.data)).all()
        kwargs.setdefault('data-role', u'select2-tags')
        kwargs.setdefault('multiple', 'multiple')
        return super(QuerySelect2TagsWidget, self).__call__(field, **kwargs)

class FlowAdmin(ConductorAuthMixin, sqla.ModelView):
    edit_template = 'admin/purchasing_edit.html'
    create_template = 'admin/purchasing_create.html'

    form_columns = ['flow_name', 'stage_order']

    form_extra_fields = {
        'stage_order': sqla.fields.QuerySelectMultipleField(
            'Stage Order', widget=QuerySelect2TagsWidget(),
            query_factory=get_stages,
            get_pk=lambda i: i.id,
            get_label=lambda i: i.name,
            allow_blank=True, blank_text='-----'
        )
    }

    def create_model(self, form, model):
        form.stage_order.data = [i.id for i in form.stage_order.data]
        super(FlowAdmin, self).create_model(form, model)

    def update_model(self, form, model):
        form.stage_order.data = [i.id for i in form.stage_order.data]
        super(FlowAdmin, self).update_model(form, model)

class StageAdmin(ConductorAuthMixin, sqla.ModelView):
    inline_models = (StageProperty, )

    form_columns = ['name', 'post_opportunities']

class UserAdmin(AuthMixin, sqla.ModelView):
    form_columns = ['email', 'first_name', 'last_name', 'department']

    form_extra_fields = {
        'department': sqla.fields.QuerySelectField(
            'Department', query_factory=department_query,
            allow_blank=True, blank_text='-----'
        )
    }

class UserRoleAdmin(SuperAdminMixin, sqla.ModelView):
    form_columns = ['email', 'first_name', 'last_name', 'department', 'role']

    form_extra_fields = {
        'department': sqla.fields.QuerySelectField(
            'Department', query_factory=department_query,
            allow_blank=True, blank_text='-----'
        ),
        'role': sqla.fields.QuerySelectField(
            'Role', query_factory=role_query,
            allow_blank=True, blank_text='-----'
        )
    }

class RoleAdmin(SuperAdminMixin, sqla.ModelView):
    form_columns = ['name']

class DocumentAdmin(AuthMixin, sqla.ModelView):
    pass

class OpportunityAdmin(AuthMixin, sqla.ModelView):
    column_list = ['contact', 'department', 'title', 'description', 'is_public']

    form_columns = [
        'contact', 'department', 'title', 'description',
        'planned_open', 'planned_deadline', 'is_public'
    ]

admin.add_view(ScoutContractAdmin(
    ContractBase, db.session, name='Contracts', endpoint='contract', category='Scout'
))
admin.add_view(CompanyAdmin(
    Company, db.session, name='Companies', endpoint='company', category='Scout'
))

admin.add_view(StageAdmin(Stage, db.session, endpoint='stage', category='Conductor'))
admin.add_view(FlowAdmin(Flow, db.session, endpoint='flow', category='Conductor'))
admin.add_view(ConductorContractAdmin(
    ContractBase, db.session, name='Contracts', endpoint='conductor-contract', category='Conductor'
))

admin.add_view(OpportunityAdmin(
    Opportunity, db.session, name='Opportunities', endpoint='opportunity', category='Beacon'
))
admin.add_view(DocumentAdmin(
    RequiredBidDocument, db.session, name='Bid Document', endpoint='bid_document', category='Beacon'
))

admin.add_view(UserAdmin(User, db.session, name='User', endpoint='user', category='Users'))
admin.add_view(UserRoleAdmin(User, db.session, name='User w/Roles', endpoint='user-roles', category='Users'))
admin.add_view(RoleAdmin(Role, db.session, endpoint='role', category='Users'))
