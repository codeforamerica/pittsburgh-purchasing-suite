# -*- coding: utf-8 -*-

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_company, insert_a_contract,
    insert_a_user, insert_a_role
)

from purchasing.data.models import ContractBase

class TestWexplorer(BaseTestCase):
    render_templates = False

    def setUp(self):
        super(TestWexplorer, self).setUp()
        # insert the users/roles
        self.admin_role = insert_a_role('admin')
        self.superadmin_role = insert_a_role('superadmin')
        self.admin_user = insert_a_user(email='foo@foo.com', role=self.admin_role)
        self.superadmin_user = insert_a_user(email='bar@foo.com', role=self.superadmin_role)

        # insert the companies/contracts
        company_1 = insert_a_company(name='BBB', insert_contract=False)
        company_2 = insert_a_company(name='ccc', insert_contract=False)
        insert_a_company(name='CCC')
        insert_a_contract(description='AAA', companies=[company_2])
        insert_a_contract(description='ddd', companies=[company_1])
        insert_a_contract(description='DDD')

    def test_explore(self):
        request = self.client.get('/wexplorer/')
        # test the request processes correctly
        self.assert200(request)
        # test that we have the wrapped form
        self.assertTrue(self.get_context_variable('search_form') is not None)

    def test_search(self):
        self.client.get('/wexplorer/search?q=aaa')
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.client.get('/wexplorer/search?q=BB')
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.client.get('/wexplorer/search?q=CC')
        self.assertEquals(len(self.get_context_variable('results')), 2)

        self.client.get('/wexplorer/search?q=dd')
        self.assertEquals(len(self.get_context_variable('results')), 2)

    def test_companies(self):
        request = self.client.get('/wexplorer/companies/1')
        # test that this works
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('company') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/wexplorer/companies/abcd'))
        self.assert404(self.client.get('/wexplorer/companies/999'))

    def test_contracts(self):
        request = self.client.get('/wexplorer/contracts/1')
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('contract') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/wexplorer/contracts/abcd'))
        self.assert404(self.client.get('/wexplorer/contracts/999'))

    def test_subscribe(self):
        # test that you can't subscribe to a contract unless you are signed in
        request = self.client.get('/wexplorer/contracts/1/subscribe')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin_user)
        request = self.client.get('/wexplorer/contracts/1/subscribe')
        self.assertEquals(len(ContractBase.query.get(1).users), 1)

        self.login_user(self.superadmin_user)
        self.client.get('/wexplorer/contracts/1/subscribe')
        self.assertEquals(len(ContractBase.query.get(1).users), 2)

        # test you can't subscribe more than once
        self.client.get('/wexplorer/contracts/1/subscribe')
        self.assertEquals(len(ContractBase.query.get(1).users), 2)

        # test you can't subscribe to a nonexistant contract
        self.assert404(self.client.get('/wexplorer/contracts/999/subscribe'))

    def test_unsubscribe(self):

        # test that you can't subscribe to a contract unless you are signed in
        request = self.client.get('/wexplorer/contracts/1/unsubscribe')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        # two followers
        self.login_user(self.admin_user)
        self.client.get('/wexplorer/contracts/1/subscribe')
        self.login_user(self.superadmin_user)
        self.client.get('/wexplorer/contracts/1/subscribe')

        self.assertEquals(len(ContractBase.query.get(1).users), 2)
        self.client.get('/wexplorer/contracts/1/unsubscribe')
        self.assertEquals(len(ContractBase.query.get(1).users), 1)
        # test you can't unsubscribe more than once
        self.client.get('/wexplorer/contracts/1/unsubscribe')
        self.assertEquals(len(ContractBase.query.get(1).users), 1)

        self.login_user(self.admin_user)
        self.client.get('/wexplorer/contracts/1/unsubscribe')
        self.assertEquals(len(ContractBase.query.get(1).users), 0)

        # test you can't unsubscribe from a nonexistant contract
        self.assert404(self.client.get('/wexplorer/contracts/999/unsubscribe'))
