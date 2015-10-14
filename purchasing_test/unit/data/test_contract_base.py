# -*- coding: utf-8 -*-

import datetime

from unittest import TestCase
from mock import Mock

from purchasing.opportunities import models
from purchasing.data import contracts, flows, stages
from purchasing.users import models

from purchasing_test.factories import (
    ContractBaseFactory, UserFactory, ContractPropertyFactory
)

class ContractObjectTestBase(TestCase):
    def setUp(self):
        super(ContractObjectTestBase, self).setUp()
        self.today = datetime.datetime.today()
        self.tomorrow = datetime.datetime.today() + datetime.timedelta(1)
        self.yesterday = datetime.datetime.today() - datetime.timedelta(1)
        self.active_contract = ContractBaseFactory.build(
            expiration_date=datetime.date.today() + datetime.timedelta(1),
            is_archived=False, parent_id=None, description='test description',
            financial_id=1234
        )

class TestContractObject(ContractObjectTestBase):
    def test_create_new_contract(self):
        '''Test contract object behaves as expected
        '''
        # test that no additional properties works
        contract_data = dict(
            description='test'
        )

        contract = ContractBaseFactory.build(**contract_data)
        self.assertEquals(contract.description, 'test')

        # test that additional properties also works
        contract_data_props = dict(
            description='test2'
        )
        contract_with_props = ContractBaseFactory.build(**contract_data_props)

        prop1 = ContractPropertyFactory.build(contract=contract_with_props)
        prop2 = ContractPropertyFactory.build(contract=contract_with_props)

        self.assertEquals(contract_with_props.description, 'test2')
        self.assertEquals(len(contract_with_props.properties), 2)
        self.assertTrue(prop1 in contract_with_props.properties)
        self.assertTrue(prop2 in contract_with_props.properties)

        # this should fail with non-existing stage
        contract_data_fails = dict(
            description='test2',
            current_stage_id=1
        )
        try:
            ContractBaseFactory.build(**contract_data_fails)
            # this should never work, so break the tests if we get here
            self.assertTrue(False)
        except:
            self.assertTrue(True)

    def test_active_contract_status(self):
        '''Test active scout contract status
        '''
        self.assertEquals(self.active_contract.scout_contract_status, 'active')

    def test_expired_replaced_contract_status(self):
        '''Test contract that is expired and replaced
        '''
        expired_replaced = ContractBaseFactory.build(
            expiration_date=self.yesterday, is_archived=True,
            children=[self.active_contract]
        )
        self.assertEquals(expired_replaced.scout_contract_status, 'expired_replaced')

    def test_replaced_contract_status(self):
        '''Test contract that is replaced
        '''
        replaced = ContractBaseFactory.build(
            expiration_date=self.tomorrow, is_archived=True,
            children=[self.active_contract]
        )
        self.assertEquals(replaced.scout_contract_status, 'replaced')

    def test_expired_contract_status(self):
        '''Test contract that is expired
        '''
        expired = ContractBaseFactory.build(
            expiration_date=self.yesterday, is_archived=True,
        )
        self.assertEquals(expired.scout_contract_status, 'expired')

    def test_archived_contract_status(self):
        '''Test contract that is archived
        '''
        archived = ContractBaseFactory.build(
            expiration_date=self.tomorrow, is_archived=True,
        )
        self.assertEquals(archived.scout_contract_status, 'archived')

    def test_no_expiration_replaced(self):
        '''Test contract that is replaced but has not expiration date
        '''
        replaced = ContractBaseFactory.build(
            is_archived=True,
            children=[self.active_contract]
        )
        self.assertEquals(replaced.scout_contract_status, 'replaced')

    def test_no_expiration_archived(self):
        '''Test contract that is archived but has no expiration date
        '''
        replaced = ContractBaseFactory.build(
            is_archived=True,
        )
        self.assertEquals(replaced.scout_contract_status, 'archived')

class TestContractFollows(ContractObjectTestBase):
    def setUp(self):
        super(TestContractFollows, self).setUp()
        self.user1 = UserFactory.build(email='user1')
        self.user2 = UserFactory.build(email='user2')
        self.active_contract.followers = [self.user1]

    def test_add_follower(self):
        self.assertEquals(len(self.active_contract.followers), 1)
        msg = self.active_contract.add_follower(self.user2)
        self.assertEquals(len(self.active_contract.followers), 2)
        self.assertEquals(msg[1], 'alert-success')

    def test_add_existing_follower(self):
        self.assertEquals(len(self.active_contract.followers), 1)
        msg = self.active_contract.add_follower(self.user1)
        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(msg[1], 'alert-info')

    def test_remove_follower(self):
        self.assertEquals(len(self.active_contract.followers), 1)
        msg = self.active_contract.remove_follower(self.user2)
        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(msg[1], 'alert-warning')

    def test_remove_existing_follower(self):
        self.assertEquals(len(self.active_contract.followers), 1)
        msg = self.active_contract.remove_follower(self.user1)
        self.assertEquals(len(self.active_contract.followers), 0)
        self.assertEquals(msg[1], 'alert-success')

class TestContractRenewals(ContractObjectTestBase):
    def setUp(self):
        super(TestContractRenewals, self).setUp()
        self.user1 = UserFactory.build(email='user1')

        self.child_contract = ContractBaseFactory.build(
            expiration_date=datetime.date.today() + datetime.timedelta(1),
            is_archived=False, description='child'
        )

        self.child_contract2 = ContractBaseFactory.build(
            expiration_date=datetime.date.today() + datetime.timedelta(1),
            is_archived=False, parent_id=self.active_contract.id, description='child2'
        )

        self.active_contract.followers = [self.user1]
        self.active_contract.children.append(self.child_contract)

    def test_single_transfer_contract_relationships(self):
        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(len(self.child_contract.followers), 0)

        self.active_contract.transfer_followers_to_children()

        self.assertEquals(len(self.active_contract.followers), 0)
        self.assertEquals(len(self.child_contract.followers), 1)

    def test_multiple_transfer_contract_relationships(self):
        self.active_contract.children.append(self.child_contract2)

        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(len(self.child_contract.followers), 0)
        self.assertEquals(len(self.child_contract2.followers), 0)

        self.active_contract.transfer_followers_to_children()

        self.assertEquals(len(self.active_contract.followers), 0)
        self.assertEquals(len(self.child_contract.followers), 1)
        self.assertEquals(len(self.child_contract2.followers), 1)

    def test_contract_extension_no_delete(self):
        self.active_contract.extend(delete_children=False)

        self.assertEquals(self.active_contract.expiration_date, None)
        self.assertEquals(self.active_contract.description, 'test description')
        self.assertEquals(len(self.active_contract.children), 1)

    def test_contract_extension_delete_children(self):
        self.active_contract.children.append(self.child_contract2)

        self.child_contract.delete = Mock()
        self.child_contract2.delete = Mock()

        self.active_contract.extend()

        self.assertEquals(self.active_contract.expiration_date, None)
        self.assertEquals(self.active_contract.description, 'test description')
        self.assertTrue(self.child_contract.delete.called)
        self.assertTrue(self.child_contract2.delete.called)
        self.assertEquals(len(self.active_contract.children), 0)

    def test_contract_kill(self):
        self.active_contract.kill()
        self.assertTrue(self.active_contract.is_archived)
        self.assertFalse(self.active_contract.is_visible)
        self.assertTrue(self.active_contract.description, 'test description [Archived]')

    def test_contract_complete(self):
        self.active_contract.complete()

        self.assertEquals(len(self.active_contract.followers), 0)
        self.assertTrue(self.active_contract.is_archived)
        self.assertFalse(self.active_contract.is_visible)
        self.assertTrue(self.active_contract.description, 'test description [Archived]')

        self.assertEquals(len(self.child_contract.followers), 1)
        self.assertFalse(self.child_contract.is_archived)
        self.assertTrue(self.child_contract.is_visible)

    def test_complete_multiple(self):
        self.active_contract.children.append(self.child_contract2)

        self.active_contract.complete()

        self.assertEquals(len(self.active_contract.followers), 0)
        self.assertTrue(self.active_contract.is_archived)
        self.assertFalse(self.active_contract.is_visible)
        self.assertTrue(self.active_contract.description, 'test description [Archived]')

        for child in [self.child_contract, self.child_contract2]:
            self.assertEquals(len(child.followers), 1)
            self.assertFalse(self.child_contract.is_archived)
            self.assertTrue(self.child_contract.is_visible)

    def test_contract_clone(self):
        self.active_contract.is_visible = True
        clone = contracts.ContractBase.clone(self.active_contract, strip=False, new_conductor_contract=False)

        self.assertTrue(clone.id is None)
        self.assertEquals(self.active_contract.description, clone.description)
        self.assertEquals(self.active_contract.expiration_date, clone.expiration_date)
        self.assertEquals(self.active_contract.contract_href, clone.contract_href)
        self.assertTrue(clone.is_visible)

        self.assertEquals(clone.parent_id, self.active_contract.id)

        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(len(clone.companies), 0)
        self.assertEquals(len(clone.followers), 0)

    def test_contract_clone_strip(self):
        self.active_contract.is_visible = True
        clone = contracts.ContractBase.clone(self.active_contract, new_conductor_contract=False)

        self.assertTrue(clone.id is None)
        self.assertTrue(clone.expiration_date is None)
        self.assertTrue(clone.financial_id is None)
        self.assertTrue(clone.is_visible)

        self.assertEquals(clone.parent_id, self.active_contract.id)

        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(len(clone.companies), 0)
        self.assertEquals(len(clone.followers), 0)

    def test_contract_clone_new_conductor(self):
        self.active_contract.is_visible = True
        clone = contracts.ContractBase.clone(self.active_contract)

        self.assertTrue(clone.id is None)
        self.assertTrue(clone.expiration_date is None)
        self.assertTrue(clone.financial_id is None)
        self.assertFalse(clone.is_visible)
        self.assertFalse(clone.is_archived)

        self.assertEquals(clone.parent_id, self.active_contract.id)

        self.assertEquals(len(self.active_contract.followers), 1)
        self.assertEquals(len(clone.companies), 0)
        self.assertEquals(len(clone.followers), 0)

    def test_contract_clone_keep_assignment(self):
        self.active_contract.assigned_to = self.user1.id

        clone = contracts.ContractBase.clone(self.active_contract)

        self.assertTrue(clone.id is None)
        self.assertTrue(clone.expiration_date is None)
        self.assertTrue(clone.financial_id is None)
        self.assertFalse(clone.is_visible)
        self.assertFalse(clone.is_archived)
        self.assertEquals(clone.parent_id, self.active_contract.id)
        self.assertEquals(clone.assigned_to, self.user1.id)
