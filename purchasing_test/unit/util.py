# -*- coding: utf-8 -*-

from purchasing.data.models import (
    ContractBase, ContractProperty,
    Stage, StageProperty, Flow
)

def insert_a_contract():
    contract_data = dict(
        contract_type='test',
        description='test2',
    )

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

    return contract.contract_properties.first()

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

    return stage.stage_properties.first()

def insert_a_flow(name='test', stage_ids=None):
    flow = Flow.create(**{
        'flow_name': name,
        'stage_order': stage_ids
    })

    return flow
