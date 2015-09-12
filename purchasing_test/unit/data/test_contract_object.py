import datetime

from unittest import TestCase
from purchasing_test.unit.factories import (
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
            is_archived=False, parent_id=None
        )

class ContractObjectTest(ContractObjectTestBase):
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
