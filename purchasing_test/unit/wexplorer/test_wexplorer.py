# -*- coding: utf-8 -*-

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import insert_a_company, insert_a_contract

class TestWexplorer(BaseTestCase):
    render_templates = False

    def setUp(self):
        super(TestWexplorer, self).setUp()
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
