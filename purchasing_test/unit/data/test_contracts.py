# -*- coding: utf-8 -*-

import datetime

from purchasing.data.models import ContractBase, ContractProperty
from purchasing.data.contracts import (
    create_new_contract, update_contract, update_contract_property,
    delete_contract, get_all_contracts, extend_a_contract,
    complete_contract, transfer_contract_relationships, clone_a_contract
)

from purchasing_test.unit.test_base import BaseTestCase, db
from purchasing_test.unit.util import (
    insert_a_contract, get_a_property
)
from purchasing_test.unit.factories import ContractBaseFactory, UserFactory

class ContractRenewalTest(BaseTestCase):
    def setUp(self):
        db.create_all()
        user = UserFactory.create()
        self.contract1 = ContractBaseFactory.create(
            financial_id=1234, expiration_date=datetime.date(2015, 1, 1),
            description='foobarbaz', followers=[user], starred=[user]
        )
        self.contract2 = ContractBaseFactory.create()
        self.contract2.parent = self.contract1
        db.session.commit()

    def test_extend_a_contract(self):
        '''Test extend contract sets properties, financial ids, deletes
        '''
        extend_a_contract(self.contract2.id, delete_child=True)

        self.assertTrue(self.contract1.expiration_date is None)
        self.assertEquals(self.contract1.financial_id, 1234)

        self.assertTrue(ContractBase.query.count(), 1)

    def test_complete_contract(self):
        '''Test visibility for completed contracts
        '''
        old_description = self.contract1.description
        child = complete_contract(self.contract1, self.contract2)

        self.assertTrue(child.is_visible)
        self.assertFalse(child.is_archived)
        self.assertTrue(self.contract1.is_archived)
        self.assertEquals(self.contract1.description, old_description + ' [Archived]')

    def test_transfer_contract_relationships(self):
        '''Test transfer followers, stars properly
        '''
        transfer_contract_relationships(self.contract1, self.contract2)

        self.assertEquals(len(self.contract1.followers), 0)
        self.assertEquals(len(self.contract2.followers), 1)

        self.assertEquals(len(self.contract1.starred), 0)
        self.assertEquals(len(self.contract2.starred), 1)

    def test_clone_a_contract(self):
        '''Test contract clones proper fields, doesn't clone improper fields
        '''
        clone = clone_a_contract(self.contract1)

        self.assertEquals(clone.description, self.contract1.description)
        self.assertTrue(clone.financial_id is None)
        self.assertTrue(clone.expiration_date is None)
        self.assertEquals(len(clone.followers), 0)

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
