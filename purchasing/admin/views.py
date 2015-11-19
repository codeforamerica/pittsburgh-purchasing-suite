# -*- coding: utf-8 -*-

from flask import request

from wtforms.ext.sqlalchemy.fields import QuerySelectField

from purchasing.extensions import admin, db
from purchasing.decorators import AuthMixin, SuperAdminMixin, ConductorAuthMixin
from purchasing.utils import localize_and_strip
from flask_admin.contrib import sqla
from flask_admin.form.widgets import Select2Widget

from purchasing.data.contracts import ContractBase, ContractProperty, ContractType, LineItem
from purchasing.data.contract_stages import ContractStage
from purchasing.data.companies import Company, CompanyContact, company_contract_association_table
from purchasing.data.flows import Flow
from purchasing.data.stages import Stage

from purchasing.opportunities.models import RequiredBidDocument, Category

from purchasing.conductor.forms import validate_integer
from purchasing.extensions import login_manager
from purchasing.users.models import User, Role, Department
from purchasing.public.models import AcceptedEmailDomains
from purchasing.opportunities.models import Opportunity

GLOBAL_EXCLUDE = [
    'created_at', 'updated_at', 'created_by', 'updated_by'
]

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

class BaseModelViewAdmin(sqla.ModelView):
    form_excluded_columns = GLOBAL_EXCLUDE
    column_exclude_list = GLOBAL_EXCLUDE

class CompanyAdmin(AuthMixin, BaseModelViewAdmin):
    inline_models = ((CompanyContact, dict(form_excluded_columns=GLOBAL_EXCLUDE)),)

    column_searchable_list = ('company_name',)

    form_columns = [
        'company_name', 'contracts'
    ]

class ContractBaseAdmin(AuthMixin, BaseModelViewAdmin):
    '''Base model for different representations of contracts
    '''
    edit_template = 'admin/purchasing_edit.html'
    create_template = 'admin/purchasing_create.html'

    column_searchable_list = (
        ContractBase.description, ContractProperty.value, Company.company_name
    )

    column_list = [
        'contract_type', 'description', 'financial_id', 'expiration_date',
        'properties', 'companies', 'is_archived'
    ]

    column_labels = dict(
        contract_href='Link to Contract PDF', financial_id='Controller #',
        properties='Contract Properties', expiration_date='Expiration', is_archived='Archived',
    )

    form_args = {
        'financial_id': {
            'validators': [validate_integer]
        },
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
    inline_models = (
        (ContractProperty, dict(form_excluded_columns=GLOBAL_EXCLUDE)),
        (LineItem, dict(form_excluded_columns=GLOBAL_EXCLUDE)),
    )

    column_editable_list = [
        'description', 'expiration_date', 'financial_id'
    ]

    form_columns = [
        'contract_type', 'description', 'properties',
        'financial_id', 'expiration_date', 'contract_href', 'parent',
        'companies', 'followers', 'is_archived', 'department',
        'is_visible'
    ]

    form_widget_args = {
        'parent': {'disabled': True}
    }

    column_labels = dict(
        contract_href='Link to Contract PDF', financial_id='Controller #',
        properties='Contract Properties', expiration_date='Expiration', is_archived='Archived',
        is_visible='Visible in Conductor'
    )

    def get_query(self):
        '''Override default get query to limit to assigned contracts
        '''
        return super(ScoutContractAdmin, self).get_query().filter(
            ContractBase.current_stage_id == None
        )

    def get_count_query(self):
        '''Override default get count query to conform to above
        '''
        return super(ScoutContractAdmin, self).get_count_query().filter(
            ContractBase.current_stage_id == None,
        )

class ConductorContractStageAdmin(SuperAdminMixin, ContractBaseAdmin):
    column_searchable_list = (
        ContractBase.description, Stage.name
    )

    column_list = [
        'contract', 'stage', 'entered', 'exited'
    ]

    form_columns = [
        'contract', 'stage', 'entered', 'exited'
    ]

    def init_search(self):
        return super(BaseModelViewAdmin, self).init_search()

    def scaffold_filters(self, name):
        return super(BaseModelViewAdmin, self).scaffold_filters()

class ConductorContractAdmin(ContractBaseAdmin):
    inline_models = (
        (ContractProperty, dict(form_excluded_columns=GLOBAL_EXCLUDE)),
    )

    column_list = [
        'description', 'expiration_date', 'current_stage', 'current_flow', 'assigned',
        'is_archived'
    ]

    form_columns = [
        'contract_type', 'description', 'assigned',
        'current_stage', 'current_flow', 'parent',
        'contract_href', 'is_archived',
        'financial_id', 'expiration_date',
    ]

    form_widget_args = {
        'current_flow': {'disabled': True},
        'current_stage': {'disabled': True},
        'parent': {'disabled': True}
    }

    def get_query(self):
        '''Override default get query to limit to assigned contracts
        '''
        return super(ConductorContractAdmin, self).get_query().filter(
            ContractBase.current_stage_id != None,
            ContractBase.is_visible == False,
        )

    def get_count_query(self):
        '''Override default get count query to conform to above
        '''
        return super(ConductorContractAdmin, self).get_count_query().filter(
            ContractBase.current_stage_id != None,
            ContractBase.is_visible == False,
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
        return self.session.query(User).join(
            Role, User.role_id == Role.id
        ).filter(
            Role.name.in_(['conductor', 'admin', 'superadmin'])
        )

def get_stages():
    return Stage.query.order_by(Stage.name)

class ContractTypeAdmin(AuthMixin, BaseModelViewAdmin):
    form_columns = [
        'name', 'allow_opportunities', 'managed_by_conductor',
        'opportunity_response_instructions'
    ]

class DepartmentAdmin(AuthMixin, BaseModelViewAdmin):
    form_excluded_columns = GLOBAL_EXCLUDE + ['users', 'opportunities', 'contracts']

class QuerySelect2TagsWidget(Select2Widget):
    def __init__(self, *args, **kwargs):
        super(QuerySelect2TagsWidget, self).__init__(*args, **kwargs)

    def __call__(self, field, **kwargs):
        current_stages = field.data

        if len(field.data) > 0 and isinstance(field.data[0], int):
            stages = Stage.query.filter(Stage.id.in_(current_stages)).all()
        else:
            stages = field.data

        field.data = [y for (x, y) in sorted(zip(current_stages, stages))]

        kwargs.setdefault('data-stage-order', u','.join([unicode(i) for i in field.data]))
        kwargs.setdefault('data-role', u'select2-tags')
        kwargs.setdefault('multiple', u'multiple')

        return super(QuerySelect2TagsWidget, self).__call__(field, **kwargs)

class FlowAdmin(ConductorAuthMixin, BaseModelViewAdmin):
    edit_template = 'admin/purchasing_edit.html'
    create_template = 'admin/purchasing_create.html'
    can_edit = False
    can_delete = False

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

    def create_model(self, form):
        form.stage_order.data = [int(i) for i in request.form.getlist('stage_order')]
        super(FlowAdmin, self).create_model(form)

    def update_model(self, form, model):
        form.stage_order.data = [int(i) for i in request.form.getlist('stage_order')]
        super(FlowAdmin, self).update_model(form, model)

class StageAdmin(ConductorAuthMixin, BaseModelViewAdmin):
    can_delete = False

    form_columns = ['name', 'post_opportunities', 'default_message']

class EmailDomainAdmin(AuthMixin, BaseModelViewAdmin):
    pass

class UserAdmin(AuthMixin, BaseModelViewAdmin):
    form_columns = ['email', 'first_name', 'last_name', 'department', 'role']

    form_extra_fields = {
        'department': sqla.fields.QuerySelectField(
            'Department', query_factory=Department.query_factory,
            allow_blank=True, blank_text='-----'
        ),
        'role': sqla.fields.QuerySelectField(
            'Role', query_factory=Role.no_admins,
            allow_blank=True, blank_text='-----'
        )
    }

    def get_query(self):
        '''Override default get query to limit to assigned contracts
        '''
        return super(UserAdmin, self).get_query().join(
            Role, User.role_id == Role.id
        ).filter(
            db.func.lower(Role.name) != 'superadmin'
        )

    def get_count_query(self):
        '''Override default get count query to conform to above
        '''
        return super(UserAdmin, self).get_count_query().join(
            Role, User.role_id == Role.id
        ).filter(
            db.func.lower(Role.name) != 'superadmin'
        )

class UserRoleAdmin(SuperAdminMixin, BaseModelViewAdmin):
    form_columns = ['email', 'first_name', 'last_name', 'department', 'role']

    form_extra_fields = {
        'department': sqla.fields.QuerySelectField(
            'Department', query_factory=Department.query_factory,
            allow_blank=True, blank_text='-----'
        ),
        'role': sqla.fields.QuerySelectField(
            'Role', query_factory=Role.query_factory,
            allow_blank=True, blank_text='-----'
        )
    }

class RoleAdmin(SuperAdminMixin, BaseModelViewAdmin):
    form_columns = ['name']

class DocumentAdmin(AuthMixin, BaseModelViewAdmin):
    pass

class OpportunityAdmin(AuthMixin, BaseModelViewAdmin):
    can_create = False
    can_edit = False

    column_list = ['contact', 'department', 'title', 'description', 'is_public', 'is_archived']

    form_columns = [
        'contact', 'department', 'title', 'description', 'planned_publish',
        'planned_submission_start', 'planned_submission_end',
        'is_archived'
    ]

    def update_model(self, form, model):
        for i in ['planned_publish', 'planned_submission_start', 'planned_submission_end']:
            form[i].data = localize_and_strip(form[i].data)

        super(OpportunityAdmin, self).update_model(form, model)

class CategoryAdmin(AuthMixin, BaseModelViewAdmin):
    column_list = ['category', 'category_friendly_name']
    form_columns = ['category', 'category_friendly_name']

    column_labels = dict(
        category='Category Group', category_friendly_name='Category Name'
    )

    form_extra_fields = {
        'category': QuerySelectField(
            'Stage Order',
            query_factory=Category.parent_category_query_factory,
            get_pk=lambda i: i.category,
            get_label=lambda i: i.category,
        )
    }

admin.add_view(ScoutContractAdmin(
    ContractBase, db.session, name='Contracts', endpoint='contract', category='Scout'
))
admin.add_view(CompanyAdmin(
    Company, db.session, name='Companies', endpoint='company', category='Scout'
))
admin.add_view(ContractTypeAdmin(
    ContractType, db.session, name='Contract Types', endpoint='contract-type', category='Scout'
))
admin.add_view(DepartmentAdmin(
    Department, db.session, name='Departments', endpoint='department', category='Scout'
))

admin.add_view(StageAdmin(Stage, db.session, endpoint='stage', category='Conductor'))
admin.add_view(FlowAdmin(Flow, db.session, endpoint='flow', category='Conductor'))
admin.add_view(ConductorContractAdmin(
    ContractBase, db.session, name='Contracts', endpoint='conductor-contract', category='Conductor'
))
admin.add_view(ConductorContractStageAdmin(
    ContractStage, db.session, name='Contract Stages', endpoint='contract-stages', category='Conductor'
))

admin.add_view(OpportunityAdmin(
    Opportunity, db.session, name='Opportunities', endpoint='opportunity', category='Beacon'
))
admin.add_view(DocumentAdmin(
    RequiredBidDocument, db.session, name='Bid Document', endpoint='bid_document', category='Beacon'
))
admin.add_view(CategoryAdmin(Category, db.session, name='Categories', endpoint='category', category='Beacon'))

admin.add_view(UserAdmin(User, db.session, name='User', endpoint='user', category='Users'))
admin.add_view(UserRoleAdmin(User, db.session, name='User w/Roles', endpoint='user-roles', category='Users'))
admin.add_view(RoleAdmin(Role, db.session, endpoint='role', category='Users'))
admin.add_view(EmailDomainAdmin(AcceptedEmailDomains, db.session, endpoint='domains', category='Users'))
