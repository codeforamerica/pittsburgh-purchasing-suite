# -*- coding: utf-8 -*-
from flask import url_for, request

from wtforms.fields import SelectField
from purchasing.extensions import admin, db
from purchasing.decorators import AuthMixin, SuperAdminMixin
from flask_admin.contrib import sqla
from flask.ext.admin.form.fields import Select2TagsField
from flask_login import current_user
from purchasing.data.models import (
    Stage, StageProperty, Flow, ContractBase, ContractProperty,
    Company, CompanyContact, LineItem
)
from purchasing.opportunities.models import RequiredBidDocument
from purchasing.extensions import login_manager
from purchasing.users.models import User, Role, DEPARTMENT_CHOICES
from purchasing.opportunities.models import Opportunity, Category

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(int(userid))

class StageAdmin(AuthMixin, sqla.ModelView):
    inline_models = (StageProperty, )

    form_columns = ['name', 'send_notifs', 'post_opportunities']

class ContractBaseAdmin(AuthMixin, sqla.ModelView):
    '''Base model for different representations of contracts
    '''
    column_labels = dict(financial_id='Controller Number')
    column_searchable_list = ('description', 'contract_type')

class ScoutContractAdmin(ContractBaseAdmin):
    inline_models = (ContractProperty, LineItem,)

    form_columns = [
        'contract_type', 'description', 'properties',
        'financial_id', 'expiration_date', 'contract_href',
        'companies', 'followers', 'starred', 'is_archived'
    ]

    column_labels = dict(contract_href='Link to Contract PDF')

    column_list = [
        'contract_type', 'description', 'financial_id', 'expiration_date',
        'is_archived'
    ]

class ConductorContractAdmin(ContractBaseAdmin):
    inline_models = (ContractProperty,)

    column_list = [
        'description', 'expiration_date', 'current_stage', 'current_flow', 'assigned'
    ]

    form_columns = [
        'contract_type', 'description', 'properties', 'expiration_date',
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
        ).all()

class CompanyAdmin(AuthMixin, sqla.ModelView):
    inline_models = (CompanyContact,)

    column_searchable_list = ('company_name',)

    form_columns = [
        'company_name', 'contracts'
    ]

def _stage_lookup(stage_name):
    return Stage.query.filter(Stage.id == stage_name).first().id

class FlowAdmin(AuthMixin, sqla.ModelView):
    form_columns = ['flow_name', 'stage_order']

    form_extra_fields = {
        'stage_order': Select2TagsField(
            'Stage Order', coerce=_stage_lookup,
            save_as_list=True
        )
    }

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

    form_overrides = dict(department=SelectField)
    form_args = dict(department={
        'choices': DEPARTMENT_CHOICES
    })

class RoleAdmin(SuperAdminMixin, sqla.ModelView):
    pass

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
