# -*- coding: utf-8 -*-

import datetime
from purchasing.database import db
from sqlalchemy.exc import IntegrityError

from purchasing.data.contracts import ContractBase
from purchasing.data.stages import Stage
from purchasing.data.flows import Flow

from purchasing.users.models import Role, User
from purchasing_test.factories import (
    UserFactory, RoleFactory, StageFactory, FlowFactory, DepartmentFactory,
    StagePropertyFactory, ContractBaseFactory, ContractPropertyFactory,
    CompanyFactory, OpportunityFactory, RequiredBidDocumentFactory
)

def insert_a_contract(properties=None, **kwargs):
    contract_data = dict(
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

    return contract.properties[0]

def insert_a_stage(name='foo', send_notifs=False, post_opportunities=False, default_message=''):
    stage = StageFactory.create(**{
        'name': name,
        'post_opportunities': post_opportunities,
        'default_message': default_message
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
    return UserFactory(
        email=email, first_name='foo', last_name='foo',
        department=DepartmentFactory.create(name=department), role=role
    )

def insert_a_user(email=None, department=None, role=None):
    role = role if role else RoleFactory.create()
    try:
        if email:
            user = UserFactory.create(email=email, role=role, department=department)
        else:
            user = UserFactory.create(role=role, department=department)
        return user
    except IntegrityError:
        db.session.rollback()
        return User.query.filter(User.email == email).first()

def insert_a_role(name):
    try:
        role = RoleFactory(name=name)
        role.save()
        return role
    except IntegrityError:
        db.session.rollback()
        return Role.query.filter(Role.name == name).first()

def get_a_role(name):
    return Role.query.filter(Role.name == name).first()

def insert_a_document(name='Foo', description='Bar'):
    document = RequiredBidDocumentFactory.create(**dict(
        display_name=name, description=description
    ))

    return document

def insert_an_opportunity(
    contact=None, department=None,
    title='Test', description='Test',
    planned_publish=datetime.datetime.today(),
    planned_submission_start=datetime.datetime.today(),
    planned_submission_end=datetime.datetime.today() + datetime.timedelta(1),
    required_documents=[], categories=set(),
    created_from_id=None, created_by=None, is_public=True
):
    department = department if department else DepartmentFactory()
    opportunity = OpportunityFactory.create(**dict(
        department_id=department.id, contact=contact, title=title,
        description=description, planned_publish=planned_publish,
        planned_submission_start=planned_submission_start,
        planned_submission_end=planned_submission_end,
        created_from_id=created_from_id, created_by=created_by,
        is_public=is_public, categories=categories
    ))

    return opportunity
