# -*- coding: utf-8 -*-

from flask_login import current_user
from purchasing.extensions import mail
from purchasing_test.test_base import BaseTestCase
from purchasing_test.util import (
    insert_a_company, insert_a_contract,
    insert_a_user, insert_a_role
)
from purchasing_test.factories import DepartmentFactory

from purchasing.data.contracts import ContractBase, LineItem, ContractNote

class Testscout(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(Testscout, self).setUp()
        # insert departments
        self.department1 = DepartmentFactory()

        # insert the users/roles
        self.admin_role = insert_a_role('admin')
        self.superadmin_role = insert_a_role('superadmin')
        self.admin_user = insert_a_user(
            email='foo@foo.com', role=self.admin_role, department=self.department1
        )
        self.superadmin_user = insert_a_user(
            email='bar@foo.com', role=self.superadmin_role, department=self.department1
        )

        # insert the companies/contracts
        self.company1 = insert_a_company(name='ship', insert_contract=False)
        self.company2 = insert_a_company(name='boat', insert_contract=False)
        insert_a_contract(
            description='vessel', companies=[self.company2], line_items=[LineItem(description='NAVY')]
        )
        self.contract1 = insert_a_contract(
            description='sail', financial_id=123, companies=[self.company1],
            line_items=[LineItem(description='sunfish')]
        )
        self.contract2 = insert_a_contract(
            description='sunfish', financial_id=456
        )

    def test_explore(self):
        '''Ensure explore endpoint works as expected
        '''
        request = self.client.get('/scout/')
        # test the request processes correctly
        self.assert200(request)
        # test that we have the wrapped form
        self.assertTrue(self.get_context_variable('search_form') is not None)

    def test_companies(self):
        '''Test that the companies page works as expected, including throwing 404s where appropriate
        '''
        request = self.client.get('/scout/companies/{}'.format(self.company1.id))
        # test that this works
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('company') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/scout/companies/abcd'))
        self.assert404(self.client.get('/scout/companies/999'))

    def test_contracts(self):
        '''Test that the contracts page works as expected, including throwing 404s where appropriate
        '''
        request = self.client.get('/scout/contracts/{}'.format(self.contract1.id))
        self.assert200(request)
        # test that we have the wrapped form and the company object
        self.assertTrue(self.get_context_variable('search_form') is not None)
        self.assertTrue(self.get_context_variable('contract') is not None)
        # test that invalid company ids 404
        self.assert404(self.client.get('/scout/contracts/abcd'))
        self.assert404(self.client.get('/scout/contracts/999'))

    def test_subscribe(self):
        '''Test all possible combinations of subscribing to a contract
        '''
        # test that you can't subscribe to a contract unless you are signed in
        request = self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')

        self.login_user(self.admin_user)
        request = self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 1)

        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 2)

        # test you can't subscribe more than once
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 2)

        # test you can't subscribe to a nonexistant contract
        self.assert404(self.client.get('/scout/contracts/999/subscribe'))

    def test_unsubscribe(self):
        '''Test ability to unsubscribe from a contract
        '''
        # test that you can't subscribe to a contract unless you are signed in
        request = self.client.get('/scout/contracts/{}/unsubscribe'.format(self.contract1.id))
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')

        # two followers
        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))

        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 2)
        self.client.get('/scout/contracts/{}/unsubscribe'.format(self.contract1.id))
        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 1)
        # test you can't unsubscribe more than once
        self.client.get('/scout/contracts/{}/unsubscribe'.format(self.contract1.id))
        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 1)

        self.login_user(self.admin_user)
        self.client.get('/scout/contracts/{}/unsubscribe'.format(self.contract1.id))
        self.assertEquals(len(ContractBase.query.get(self.contract1.id).followers), 0)

        # test you can't unsubscribe from a nonexistant contract
        self.assert404(self.client.get('/scout/contracts/999/unsubscribe'))

    def test_department_filter(self):
        '''Test that filter page works properly and shows the error where appropriate
        '''
        self.login_user(self.admin_user)
        # assert it works with no subscriptions
        self.assert200(self.client.get('/scout/filter/{}'.format(self.admin_user.department_id)))

        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract2.id))

        self.login_user(self.superadmin_user)
        self.client.get('/scout/contracts/{}/subscribe'.format(self.contract1.id))

        # ensure that when we have a follower, the contract page loads as expected
        self.assert200(self.client.get('/scout/contracts/{}'.format(self.contract1.id)))

        # filter by contracts associated with Other department
        # assert it works with multiple subscriptions
        self.client.get('/scout/filter/{}'.format(self.admin_user.department_id))
        self.assertEquals(len(self.get_context_variable('results')), 2)
        # assert that contract 1 is first
        self.assertEquals(self.get_context_variable('results')[0].id, self.contract1.id)
        self.assertEquals(self.get_context_variable('results')[0].follows, 2)

        # assert that the department must be a real department
        request = self.client.get('/scout/filter/FAKEFAKEFAKE')
        self.assertEquals(request.status_code, 404)

    def test_notes(self):
        '''Test taking notes on scout
        '''
        # assert you can't take a note on a contract
        self.assertEquals(ContractNote.query.count(), 0)
        self.client.post('/scout/contracts/{}'.format(self.contract1.id), data=dict(note='test', user=current_user.id))
        self.assertEquals(ContractNote.query.count(), 0)

        self.login_user(self.admin_user)
        self.client.post('/scout/contracts/{}'.format(self.contract1.id), data={
            'note': 'NOTENOTENOTE', 'user': self.admin_user.id
        })
        self.assertEquals(ContractNote.query.count(), 1)

        has_note = self.client.get('/scout/contracts/{}'.format(self.contract1.id))
        self.assertTrue('NOTENOTENOTE' in has_note.data)

        # make sure the note doesn't show up for other people
        self.login_user(self.superadmin_user)
        no_note = self.client.get('/scout/contracts/{}'.format(self.contract1.id))
        self.assertTrue('NOTENOTENOTE' not in no_note.data)

        self.logout_user()
        no_note_two = self.client.get('/scout/contracts/{}'.format(self.contract1.id))
        self.assertTrue('NOTENOTENOTE' not in no_note_two.data)

    def test_feedback(self):
        '''Test scout contract feedback mechanism
        '''
        self.assert200(self.client.get('/scout/contracts/{}/feedback'.format(self.contract1.id)))
        self.assert_template_used('scout/feedback.html')

        self.assert404(self.client.get('/scout/contracts/1000/feedback'))

        # assert data validation
        bad_post = self.client.post('/scout/contracts/{}/feedback'.format(self.contract1.id), data=dict(
            sender='JUNK'
        ))

        self.assert200(bad_post)
        # correct template
        self.assert_template_used('scout/feedback.html')
        # two alerts
        self.assertTrue(bad_post.data.count('alert-danger'), 2)
        # feedback is required
        self.assertTrue(bad_post.data.count('field is required'), 1)
        # email must be email
        self.assertTrue(bad_post.data.count('Invalid'), 1)

        # assert email works properly
        self.login_user(self.admin_user)
        self.admin_user.email = 'foo@foo.com'

        with mail.record_messages() as outbox:
            success_post = self.client.post('/scout/contracts/{}/feedback'.format(self.contract1.id), data=dict(
                body='test'
            ))

            # the mail sent
            self.assertEquals(len(outbox), 1)
            # it went to the right place
            self.assertTrue(self.admin_user.email in outbox[0].send_to)
            # it redirects and flashes correctly
            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/scout/contracts/{}'.format(self.contract1.id))
            self.assert_flashes('Thank you for your feedback!', 'alert-success')
