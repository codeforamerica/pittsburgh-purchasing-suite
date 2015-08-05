# -*- coding: utf-8 -*-

import datetime
from purchasing.database import db
from sqlalchemy.exc import IntegrityError
from purchasing.data.models import (
    ContractBase, ContractProperty,
    Stage, StageProperty, Flow, Company
)
from purchasing.users.models import Role
from purchasing_test.unit.factories import (
    UserFactory, RoleFactory, StageFactory, FlowFactory,
    StagePropertyFactory, ContractBaseFactory, ContractPropertyFactory,
    CompanyFactory, OpportunityFactory, RequiredBidDocumentFactory
)
from purchasing.opportunities.models import Opportunity, RequiredBidDocument

def insert_a_contract(properties=None, **kwargs):
    contract_data = dict(
        contract_type='test',
        description='test2',
    ) if not kwargs else dict(kwargs)

    contract = ContractBaseFactory.create(**contract_data)

    if properties:
        [i.update({'contract': contract}) for i in properties]
    else:
        properties = [
            dict(contract=contract, key='foo', value='bar'),
            dict(contract=contract, key='baz', value='qux')
        ]

    for _property in properties:
        ContractPropertyFactory.create(**_property)
    return contract

def get_a_property():
    contract = ContractBase.query.first()
    if not contract:
        contract = insert_a_contract()

    return contract.properties.first()

def insert_a_stage(name='foo', send_notifs=False, post_opportunities=False):
    stage = StageFactory.create(**{
        'name': name,
        'post_opportunities': post_opportunities
    })

    properties = [
        dict(stage=stage, key='foo', value='bar'),
        dict(stage=stage, key='baz', value='qux')
    ]

    for property in properties:
        StagePropertyFactory.create(**property)
    return stage

def get_a_stage_property():
    stage = Stage.query.first()
    if not stage:
        stage = insert_a_stage()

    return stage.properties.first()

def insert_a_flow(name='test', stage_ids=None):
    try:
        flow = FlowFactory.create(**{
            'flow_name': name,
            'stage_order': stage_ids
        })

        return flow
    except IntegrityError:
        db.session.rollback()
        return Flow.query.filter(Flow.name == name).first()


def insert_a_company(name='test company', insert_contract=True):
    if insert_contract:
        contract = insert_a_contract()
        company = CompanyFactory.create(**{
            'company_name': name,
            'contracts': [contract]
        })
    else:
        company = CompanyFactory.create(**{'company_name': name})

    return company

def create_a_user(email='foo@foo.com', department='Other', role=None):
    return UserFactory(email=email, first_name='foo', last_name='foo', department=department, role=role)

def insert_a_user(email='foo@foo.com', department='Other', role=None):
    try:
        user = UserFactory(
            email=email, first_name='foo', last_name='foo',
            department=department, role=role
        )
        user.save()
        return user
    except IntegrityError:
        db.session.rollback()
        pass

def insert_a_role(name):
    try:
        role = RoleFactory(name=name)
        role.save()
        return role
    except IntegrityError:
        db.session.rollback()
        pass

def get_a_role(name):
    return Role.query.filter(Role.name == name).first()

def insert_a_document(name='Foo', description='Bar'):
    document = RequiredBidDocumentFactory.create(**dict(
        display_name=name, description=description
    ))

    return document

def insert_an_opportunity(
    department='Other', contact_id=None,
    title='Test', description='Test',
    planned_advertise=datetime.datetime.today(),
    planned_open=datetime.datetime.today(),
    planned_deadline=datetime.datetime.today() + datetime.timedelta(1),
    required_documents=[],
    created_from_id=None, created_by_id=None, is_public=True
):
    opportunity = OpportunityFactory.create(**dict(
        department=department, contact_id=contact_id, title=title,
        description=description, planned_advertise=planned_advertise,
        planned_open=planned_open, planned_deadline=planned_deadline,
        created_from_id=created_from_id, created_by_id=created_by_id,
        is_public=is_public
    ))

    return opportunity
