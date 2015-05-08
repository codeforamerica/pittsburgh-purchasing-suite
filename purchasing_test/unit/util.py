# -*- coding: utf-8 -*-

from purchasing.data.models import (
    ContractBase, ContractProperty,
    Stage, StageProperty, Flow, Company
)
from purchasing.users.models import User, Role

def insert_a_contract(**kwargs):
    contract_data = dict(
        contract_type='test',
        description='test2',
    ) if not kwargs else dict(kwargs)

    contract = ContractBase.create(**contract_data)

    properties = [
        dict(contract_id=contract.id, key='foo', value='bar'),
        dict(contract_id=contract.id, key='baz', value='qux')
    ]

    for property in properties:
        ContractProperty.create(**property)
    return contract

def get_a_property():
    contract = ContractBase.query.first()
    if not contract:
        contract = insert_a_contract()

    return contract.properties.first()

def insert_a_stage():
    stage = Stage.create(**{
        'name': 'foo'
    })

    properties = [
        dict(stage_id=stage.id, key='foo', value='bar'),
        dict(stage_id=stage.id, key='baz', value='qux')
    ]

    for property in properties:
        StageProperty.create(**property)
    return stage

def get_a_stage_property():
    stage = Stage.query.first()
    if not stage:
        stage = insert_a_stage()

    return stage.properties.first()

def insert_a_flow(name='test', stage_ids=None):
    flow = Flow.create(**{
        'flow_name': name,
        'stage_order': stage_ids
    })

    return flow

def insert_a_company(name='test company', insert_contract=True):
    if insert_contract:
        contract = insert_a_contract()
        company = Company.create(**{
            'company_name': name,
            'contracts': [contract]
        })
    else:
        company = Company.create(**{'company_name': name})

    return company

def create_a_user(email='foo@foo.com', department='Other', role=None):
    return User(email=email, first_name='foo', last_name='foo', department=department, role_id=role)

def insert_a_user(email='foo@foo.com', department='Other', role=None):
    user = create_a_user(email, department, role)
    user.save()
    return user

def insert_a_role(name):
    role = Role(name=name)
    role.save()
    return role.id
