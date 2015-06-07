# -*- coding: utf-8 -*-

from flask import current_app
from purchasing.extensions import mail
from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_company, insert_a_contract,
    insert_a_user, insert_a_role
)

from purchasing.data.models import ContractBase, ContractProperty, LineItem
from purchasing.data.contracts import get_one_contract

class TestWexplorer(BaseTestCase):
    render_templates = True

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
        insert_a_contract(description='ddd', companies=[company_1], line_items=[LineItem(description='fff')])
        insert_a_contract(description='DDD', financial_id=123, properties=[ContractProperty(key='foo', value='EEE')])

    def test_explore(self):
        '''
        Ensure explore endpoint works as expected
        '''
        request = self.client.get('/wexplorer/')
        # test the request processes correctly
        self.assert200(request)
        # test that we have the wrapped form
        self.assertTrue(self.get_context_variable('search_form') is not None)

    def test_search(self):
        '''
        Check all possible searches return properly: descriptions, names, properties, line items, financial ids
        '''
        self.assert200(self.client.get('/wexplorer/search?q=aaa'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/wexplorer/search?q=BB'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/wexplorer/search?q=CC'))
        self.assertEquals(len(self.get_context_variable('results')), 2)

        self.assert200(self.client.get('/wexplorer/search?q=dd'))
        self.assertEquals(len(self.get_context_variable('results')), 2)

        self.assert200(self.client.get('/wexplorer/search?q=FAKEFAKEFAKE'))
        self.assertEquals(len(self.get_context_variable('results')), 0)

        self.assert200(self.client.get('/wexplorer/search?q=EEE'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/wexplorer/search?q=ff'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/wexplorer/search?q=123'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

    def test_companies(self):
        '''
        Test that the companies page works as expected, including throwing 404s where appropriate
        '''
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
        '''
        Test that the contracts page works as expected, including throwing 404s where appropriate
        '''
        request = self.client.get('/wexplorer/contracts/1')
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('contract') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/wexplorer/contracts/abcd'))
        self.assert404(self.client.get('/wexplorer/contracts/999'))

    def test_subscribe(self):
        '''
        Tests all possible combinations of subscribing to a contract
        '''
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
        '''
        Tests ability to unsubscribe from a contract
        '''
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

    def test_star(self):
        '''
        Test starring contracts works as expected
        '''
        request = self.client.get('/wexplorer/contracts/1/star')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin_user)
        request = self.client.get('/wexplorer/contracts/1/star')
        self.assertEquals(len(ContractBase.query.get(1).starred), 1)

        self.login_user(self.superadmin_user)
        self.client.get('/wexplorer/contracts/1/star')
        self.assertEquals(len(ContractBase.query.get(1).starred), 2)

        # test you can't star more than once
        self.client.get('/wexplorer/contracts/1/star')
        self.assertEquals(len(ContractBase.query.get(1).starred), 2)

        # test you can't star to a nonexistant contract
        self.assert404(self.client.get('/wexplorer/contracts/999/star'))

    def test_unstar(self):
        '''
        Test unstarring contracts works as expected
        '''
        # test that you can't unstar to a contract unless you are signed in
        request = self.client.get('/wexplorer/contracts/1/unstar')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        # two followers
        self.login_user(self.admin_user)
        self.client.get('/wexplorer/contracts/1/star')
        self.login_user(self.superadmin_user)
        self.client.get('/wexplorer/contracts/1/star')

        self.assertEquals(len(ContractBase.query.get(1).starred), 2)
        self.client.get('/wexplorer/contracts/1/unstar')
        self.assertEquals(len(ContractBase.query.get(1).starred), 1)
        # test you can't unstar more than once
        self.client.get('/wexplorer/contracts/1/unstar')
        self.assertEquals(len(ContractBase.query.get(1).starred), 1)

        self.login_user(self.admin_user)
        self.client.get('/wexplorer/contracts/1/unstar')
        self.assertEquals(len(ContractBase.query.get(1).starred), 0)

        # test you can't unstar from a nonexistant contract
        self.assert404(self.client.get('/wexplorer/contracts/999/unstar'))

    def test_filter(self):
        '''
        Test that the filter page works properly and shows the error where appropriate
        '''
        # login as admin user and subscribe to two contracts
        self.login_user(self.admin_user)
        self.client.get('/wexplorer/contracts/1/subscribe')
        self.client.get('/wexplorer/contracts/2/subscribe')

        # login as superadmin user and subscribe to one contract
        self.login_user(self.superadmin_user)
        self.client.get('/wexplorer/contracts/1/subscribe')

        # filter base page successfully returns
        self.assert200(self.client.get('/wexplorer/filter'))

        # filter by contracts associated with Other department
        self.client.get('/wexplorer/filter/Other')
        self.assertEquals(len(self.get_context_variable('results')), 2)
        # assert that contract 1 is first
        self.assertEquals(self.get_context_variable('results')[0].id, 1)
        self.assertEquals(self.get_context_variable('results')[0].cnt, 2)

        # assert innovation and performance has no results
        self.client.get('/wexplorer/filter/Innovation and Performance')
        self.assertEquals(len(self.get_context_variable('results')), 0)

        # assert that the department must be a real department
        request = self.client.get('/wexplorer/filter/FAKEFAKEFAKE')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You must choose a valid department!', 'alert-danger')

    def test_feedback(self):
        '''
        Test wexplorer contract feedback mechanism
        '''
        self.assert200(self.client.get('/wexplorer/contracts/1/feedback'))
        self.assert_template_used('wexplorer/feedback.html')

        self.assert404(self.client.get('/wexplorer/contracts/1000/feedback'))

        contract = get_one_contract(1)

        # assert data validation
        bad_post = self.client.post('/wexplorer/contracts/1/feedback', data=dict(
            sender='JUNK'
        ))

        self.assert200(bad_post)
        # correct template
        self.assert_template_used('wexplorer/feedback.html')
        # two alerts
        self.assertTrue(bad_post.data.count('alert-danger'), 2)
        # feedback is required
        self.assertTrue(bad_post.data.count('field is required'), 1)
        # email must be email
        self.assertTrue(bad_post.data.count('Invalid'), 1)

        # assert email works properly
        self.login_user(self.admin_user)

        with mail.record_messages() as outbox:
            success_post = self.client.post('/wexplorer/contracts/1/feedback', data=dict(
                body='test'
            ))

            # the mail sent
            self.assertEquals(len(outbox), 1)
            # it went to the right place
            self.assertTrue(current_app.config['ADMIN_EMAIL'] in outbox[0].send_to)
            # assert the subject is right
            self.assertTrue(str(contract.id) in outbox[0].subject)
            self.assertTrue(contract.description in outbox[0].subject)
            # the message body contains the right email address
            self.assertTrue(self.admin_user.email in outbox[0].html)
            # it redirects and flashes correctly
            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/wexplorer/contracts/1')
            self.assert_flashes('Thank you for your feedback!', 'alert-success')
