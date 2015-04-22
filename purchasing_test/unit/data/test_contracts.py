# -*- coding: utf-8 -*-

from purchasing.data.models import ContractBase, ContractProperty
from purchasing.data.contracts import (
    create_new_contract, update_contract, update_contract_property,
    delete_contract, get_all_contracts
)

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_contract, get_a_property
)

class ContractsTest(BaseTestCase):
    def test_create_new_contract(self):
        # test that no additional properties works
        contract_data = dict(
            contract_type='test',
            description='test'
        )

        contract = create_new_contract(contract_data)
        self.assertEquals(ContractBase.query.count(), 1)
        self.assertEquals(
            ContractBase.query.first().description,
            contract.description
        )

        # test that additional properties also works
        contract_data_props = dict(
            contract_type='test',
            description='test2',
            properties=[
                dict(foo='bar'),
                dict(baz='qux')
            ]
        )

        contract_with_props = create_new_contract(contract_data_props)
        self.assertEquals(ContractBase.query.count(), 2)
        self.assertEquals(ContractProperty.query.count(), 2)
        self.assertEquals(
            ContractBase.query.all()[-1].description,
            contract_with_props.description
        )

        # this should fail with non-existing stage
        contract_data_fails = dict(
            contract_type='test',
            description='test2',
            current_stage_id=1
        )
        try:
            create_new_contract(contract_data_fails)
            # this should never work, so break the tests if we get here
            self.assertTrue(False)
        except:
            self.assertTrue(True)

    def test_update_contract(self):
        contract = insert_a_contract()

        self.assertEquals(
            ContractBase.query.first().description,
            contract.description
        )

        update_contract(contract.id, {
            'description': 'new description',
        })

        self.assertEquals(
            ContractBase.query.first().description,
            'new description'
        )

    def test_update_contract_property(self):
        property = get_a_property()

        update_contract_property(property.id, {
            'value': 'new value'
        })

        self.assertEquals(
            ContractProperty.query.get(property.id).value,
            'new value'
        )

    def test_delete_contract(self):
        contract = insert_a_contract()

        self.assertEquals(ContractBase.query.count(), 1)
        self.assertEquals(ContractProperty.query.count(), 2)

        delete_contract(contract.id)

        self.assertEquals(ContractBase.query.count(), 0)
        self.assertEquals(ContractProperty.query.count(), 0)

    def test_get_contracts(self):
        insert_a_contract()
        insert_a_contract()
        insert_a_contract()

        self.assertEquals(len(get_all_contracts()), 3)
