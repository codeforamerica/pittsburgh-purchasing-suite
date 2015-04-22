# -*- coding: utf-8 -*-

from purchasing.data.models import ContractBase, ContractProperty

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
