# -*- coding: utf-8 -*-

from flask import current_app
from purchasing.app import db
from purchasing.extensions import mail
from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_company, insert_a_contract,
    insert_a_user, get_a_role
)

from purchasing.data.models import ContractBase, LineItem
from purchasing.data.contracts import get_one_contract

class TestWexplorer(BaseTestCase):
    render_templates = True

    def setUp(self):
        from flask_migrate import upgrade
        upgrade()

        # insert the users/roles
        self.admin_role = get_a_role('admin')
        self.superadmin_role = get_a_role('superadmin')
        self.admin_user = insert_a_user(email='foo@foo.com', role=self.admin_role.id)
        self.superadmin_user = insert_a_user(email='bar@foo.com', role=self.superadmin_role.id)

        # insert the companies/contracts
        company_1 = insert_a_company(name='ship', insert_contract=False)
        company_2 = insert_a_company(name='boat', insert_contract=False)
        insert_a_contract(description='vessel', companies=[company_2], line_items=[LineItem(description='NAVY')])
        insert_a_contract(description='sail', financial_id=123, companies=[company_1], line_items=[LineItem(description='sunfish')])
        insert_a_contract(description='sunfish', financial_id=456, properties=[dict(key='foo', value='engine')])

    def tearDown(self):
        db.session.execute('''DROP SCHEMA IF EXISTS public cascade;''')
        db.session.execute('''CREATE SCHEMA public;''')
        db.session.commit()
        db.session.remove()
        db.drop_all()
        db.get_engine(self.app).dispose()

    def test_explore(self):
        '''
        Ensure explore endpoint works as expected
        '''
        request = self.client.get('/scout/')
        # test the request processes correctly
        self.assert200(request)
        # test that we have the wrapped form
        self.assertTrue(self.get_context_variable('search_form') is not None)

    def test_search(self):
        '''
        Check all possible searches return properly: descriptions, names, properties, line items, financial ids
        '''
        self.assert200(self.client.get('/scout/search?q=ship'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=boat'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=vessel'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=FAKEFAKEFAKE'))
        self.assertEquals(len(self.get_context_variable('results')), 0)

        self.assert200(self.client.get('/scout/search?q=sunfish'))
        self.assertEquals(len(self.get_context_variable('results')), 2)

        # make sure you can filter with the check boxes
        self.assert200(self.client.get('/scout/search?q=sunfish&line_item=y'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=engine'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=123'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        # check searching for everything gives you everything
        self.assert200(self.client.get('/scout/search?q='))
        self.assertEquals(len(self.get_context_variable('results')), 3)

    def test_companies(self):
        '''
        Test that the companies page works as expected, including throwing 404s where appropriate
        '''
        request = self.client.get('/scout/companies/1')
        # test that this works
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('company') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/scout/companies/abcd'))
        self.assert404(self.client.get('/scout/companies/999'))

    def test_contracts(self):
        '''
        Test that the contracts page works as expected, including throwing 404s where appropriate
        '''
        request = self.client.get('/scout/contracts/1')
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('contract') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/scout/contracts/abcd'))
        self.assert404(self.client.get('/scout/contracts/999'))

    def test_subscribe(self):
        '''
        Tests all possible combinations of subscribing to a contract
        '''
        # test that you can't subscribe to a contract unless you are signed in
        request = self.client.get('/scout/contracts/1/subscribe')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin_user)
        request = self.client.get('/scout/contracts/1/subscribe')
        self.assertEquals(len(ContractBase.query.get(1).followers), 1)

        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/1/subscribe')
        self.assertEquals(len(ContractBase.query.get(1).followers), 2)

        # test you can't subscribe more than once
        self.client.get('/scout/contracts/1/subscribe')
        self.assertEquals(len(ContractBase.query.get(1).followers), 2)

        # test you can't subscribe to a nonexistant contract
        self.assert404(self.client.get('/scout/contracts/999/subscribe'))

    def test_unsubscribe(self):
        '''
        Tests ability to unsubscribe from a contract
        '''
        # test that you can't subscribe to a contract unless you are signed in
        request = self.client.get('/scout/contracts/1/unsubscribe')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        # two followers
        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/1/subscribe')
        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/1/subscribe')

        self.assertEquals(len(ContractBase.query.get(1).followers), 2)
        self.client.get('/scout/contracts/1/unsubscribe')
        self.assertEquals(len(ContractBase.query.get(1).followers), 1)
        # test you can't unsubscribe more than once
        self.client.get('/scout/contracts/1/unsubscribe')
        self.assertEquals(len(ContractBase.query.get(1).followers), 1)

        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/1/unsubscribe')
        self.assertEquals(len(ContractBase.query.get(1).followers), 0)

        # test you can't unsubscribe from a nonexistant contract
        self.assert404(self.client.get('/scout/contracts/999/unsubscribe'))

    def test_star(self):
        '''
        Test starring contracts works as expected
        '''
        request = self.client.get('/scout/contracts/1/star')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin_user)
        request = self.client.get('/scout/contracts/1/star')
        self.assertEquals(len(ContractBase.query.get(1).starred), 1)

        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/1/star')
        self.assertEquals(len(ContractBase.query.get(1).starred), 2)

        # test you can't star more than once
        self.client.get('/scout/contracts/1/star')
        self.assertEquals(len(ContractBase.query.get(1).starred), 2)

        # test you can't star to a nonexistant contract
        self.assert404(self.client.get('/scout/contracts/999/star'))

    def test_unstar(self):
        '''
        Test unstarring contracts works as expected
        '''
        # test that you can't unstar to a contract unless you are signed in
        request = self.client.get('/scout/contracts/1/unstar')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        # two followers
        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/1/star')
        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/1/star')

        self.assertEquals(len(ContractBase.query.get(1).starred), 2)
        self.client.get('/scout/contracts/1/unstar')
        self.assertEquals(len(ContractBase.query.get(1).starred), 1)
        # test you can't unstar more than once
        self.client.get('/scout/contracts/1/unstar')
        self.assertEquals(len(ContractBase.query.get(1).starred), 1)

        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/1/unstar')
        self.assertEquals(len(ContractBase.query.get(1).starred), 0)

        # test you can't unstar from a nonexistant contract
        self.assert404(self.client.get('/scout/contracts/999/unstar'))

    def test_department_filter(self):
        '''
        Test that the filter page works properly and shows the error where appropriate
        '''
        # login as admin user and subscribe to two contracts
        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/1/subscribe')
        self.client.get('/scout/contracts/2/subscribe')

        # login as superadmin user and subscribe to one contract
        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/1/subscribe')

        # filter base page successfully returns
        self.assert200(self.client.get('/scout/filter'))

        # filter by contracts associated with Other department
        self.client.get('/scout/filter/Other')
        self.assertEquals(len(self.get_context_variable('results')), 2)
        # assert that contract 1 is first
        self.assertEquals(self.get_context_variable('results')[0].id, 1)
        self.assertEquals(self.get_context_variable('results')[0].cnt, 2)

        # assert innovation and performance has no results
        self.client.get('/scout/filter/Innovation and Performance')
        self.assertEquals(len(self.get_context_variable('results')), 0)

        # assert that the department must be a real department
        request = self.client.get('/scout/filter/FAKEFAKEFAKE')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You must choose a valid department!', 'alert-danger')

    def test_feedback(self):
        '''
        Test wexplorer contract feedback mechanism
        '''
        self.assert200(self.client.get('/scout/contracts/1/feedback'))
        self.assert_template_used('wexplorer/feedback.html')

        self.assert404(self.client.get('/scout/contracts/1000/feedback'))

        contract = get_one_contract(1)

        # assert data validation
        bad_post = self.client.post('/scout/contracts/1/feedback', data=dict(
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
            success_post = self.client.post('/scout/contracts/1/feedback', data=dict(
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
            self.assertEquals(success_post.location, 'http://localhost/scout/contracts/1')
            self.assert_flashes('Thank you for your feedback!', 'alert-success')
