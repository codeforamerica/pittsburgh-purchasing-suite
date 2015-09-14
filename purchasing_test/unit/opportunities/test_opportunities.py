# -*- coding: utf-8 -*-

import json
import datetime
from unittest import TestCase
from flask import current_app, url_for

from purchasing.extensions import mail
from purchasing.data.importer.nigp import main as import_nigp
from purchasing.opportunities.models import Vendor

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import insert_a_role, insert_a_user, insert_an_opportunity
from purchasing_test.unit.factories import OpportunityFactory, UserFactory, RoleFactory

class TestOpportunityModel(TestCase):
    def setUp(self):
        self.yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        self.today = datetime.datetime.today()
        self.tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)

    def test_opportunity_open(self):
        open_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow
        )
        self.assertTrue(open_opportunity.is_published)
        self.assertFalse(open_opportunity.is_upcoming)
        self.assertTrue(open_opportunity.is_submission_start)
        self.assertFalse(open_opportunity.is_submission_end)

    def test_opportunity_notpublic(self):
        notpublic_opportunity = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow
        )
        self.assertFalse(notpublic_opportunity.is_published)
        self.assertFalse(notpublic_opportunity.is_upcoming)
        self.assertFalse(notpublic_opportunity.is_submission_start)
        self.assertFalse(notpublic_opportunity.is_submission_end)

    def test_opportunity_pending(self):
        pending_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.tomorrow, planned_submission_end=self.tomorrow
        )
        self.assertTrue(pending_opportunity.is_published)
        self.assertTrue(pending_opportunity.is_upcoming)
        self.assertFalse(pending_opportunity.is_submission_start)
        self.assertFalse(pending_opportunity.is_submission_end)

    def test_opportunity_closed(self):
        closed_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.yesterday, planned_submission_end=self.yesterday
        )
        self.assertTrue(closed_opportunity.is_published)
        self.assertFalse(closed_opportunity.is_upcoming)
        self.assertFalse(closed_opportunity.is_submission_start)
        self.assertTrue(closed_opportunity.is_submission_end)

        closed_opportunity_today_deadline = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.yesterday, planned_submission_end=self.today
        )
        self.assertTrue(closed_opportunity_today_deadline.is_published)
        self.assertFalse(closed_opportunity_today_deadline.is_upcoming)
        self.assertFalse(closed_opportunity_today_deadline.is_submission_start)
        self.assertTrue(closed_opportunity_today_deadline.is_submission_end)

    def test_can_edit_not_public(self):
        staff = UserFactory.build(role=RoleFactory.build(name='staff'))
        creator = UserFactory.build(role=RoleFactory.build(name='staff'))
        admin = UserFactory.build(role=RoleFactory.build(name='admin'))
        opportunity = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow,
            created_by=creator, contact=creator, created_by_id=creator.id,
            contact_id=creator.id
        )
        self.assertFalse(opportunity.can_edit(staff))
        self.assertTrue(opportunity.can_edit(creator))
        self.assertTrue(opportunity.can_edit(admin))

    def test_can_edit_is_public(self):
        staff = UserFactory.build(role=RoleFactory.build(name='staff'))
        creator = UserFactory.build(role=RoleFactory.build(name='staff'))
        admin = UserFactory.build(role=RoleFactory.build(name='admin'))
        opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow,
            created_by=creator, created_by_id=creator.id,
            contact_id=creator.id
        )
        self.assertFalse(opportunity.can_edit(staff))
        self.assertFalse(opportunity.can_edit(creator))
        self.assertTrue(opportunity.can_edit(admin))

class TestOpportunities(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestOpportunities, self).setUp()
        # import our test categories
        import_nigp(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

    def test_templates(self):
        '''Test templates used, return 200
        '''
        # insert our opportunity, users
        admin_role = insert_a_role('admin')
        admin = insert_a_user(role=admin_role)

        opportunity = insert_an_opportunity(
            contact=admin, created_by=admin,
            is_public=True, planned_publish=datetime.date.today() - datetime.timedelta(1),
            planned_submission_start=datetime.date.today() + datetime.timedelta(2),
            planned_submission_end=datetime.date.today() + datetime.timedelta(2)
        )

        for rule in current_app.url_map.iter_rules():

            _endpoint = rule.endpoint.split('.')
            # filters out non-beacon endpoints
            if (len(_endpoint) > 1 and _endpoint[1] == 'static') or \
                _endpoint[0] != ('opportunities', 'opportunities_admin'):
                continue
            else:
                if '<int:' in rule.rule:
                    response = self.client.get(url_for(rule.endpoint, opportunity_id=opportunity.id))
                else:
                    response = self.client.get(rule.rule)
                self.assert200(response)

    def test_index(self):
        '''Test index page works as expected
        '''
        response = self.client.get('/beacon/')
        self.assert200(response)
        self.assert_template_used('opportunities/front/splash.html')

        self.client.post('/beacon/signup?email=BADEMAIL', follow_redirects=True)

        with self.client.session_transaction() as session:
            assert 'email' not in session

        # assert clicking signup works as expected
        signup = self.client.post('/beacon/signup?email=foo@foo.com', follow_redirects=True)
        self.assertTrue('foo@foo.com' in signup.data)

    def test_signup(self):
        '''Test signups work as expected including validation errors, signups, etc.
        '''
        admin_role = insert_a_role('admin')
        superadmin_role = insert_a_role('superadmin')

        insert_a_user(role=admin_role)
        insert_a_user(email='foo2@foo.com', role=superadmin_role)

        response = self.client.get('/beacon/signup')
        self.assert200(response)
        subcats = json.loads(self.get_context_variable('subcategories'))

        # assert three categories (plus the total category)
        self.assertEquals(len(subcats.keys()), 4)
        # assert five total subcatgories (plus 5 in the total field)
        self.assertEquals(len([item for sublist in subcats.values() for item in sublist]), 10)

        # assert email, business, categories needed
        no_email_post = self.client.post('/beacon/signup', data=dict(
            first_name='foo'
        ))

        self.assert200(no_email_post)
        self.assertTrue(no_email_post.data.count('alert-danger'), 3)
        # ensure that there are two required field notes
        self.assertTrue(no_email_post.data.count('This field is required'), 2)

        # assert valid email address
        invalid_email_post = self.client.post('/beacon/signup', data=dict(
            email='INVALID',
            business_name='test'
        ))

        self.assert200(invalid_email_post)
        self.assertTrue(invalid_email_post.data.count('alert-danger'), 1)
        self.assertTrue(invalid_email_post.data.count('Invalid email address.'), 1)

        # assert valid categories

        with mail.record_messages() as outbox:

            # successful post with only one set of subcategories
            success_post = self.client.post('/beacon/signup', data={
                'email': 'foo@foo.com',
                'business_name': 'foo',
                'subcategories-1': 'on',
                'categories': 'Apparel'
            })

            with self.client.session_transaction() as session:
                assert 'email' in session
                assert 'business_name' in session
                self.assertEquals(session['email'], 'foo@foo.com')
                self.assertEquals(session['business_name'], 'foo')

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/beacon/')
            # should send three emails
            # one to the vendor, one to the admins
            self.assertEquals(len(outbox), 2)
            self.assertEquals(Vendor.query.count(), 1)
            self.assertEquals(len(Vendor.query.first().categories), 1)
            self.assert_flashes(
                'Thank you for signing up! Check your email for more information', 'alert-success'
            )

            # successful post with two sets of subcategories
            success_post_everything = self.client.post('/beacon/signup', data={
                'email': 'foo2@foo.com',
                'business_name': 'foo',
                'subcategories-1': 'on',
                'subcategories-2': 'on',
                'subcategories-3': 'on',
                'subcategories-4': 'on',
                'subcategories-5': 'on',
                'categories': 'Apparel'
            })

            self.assertEquals(success_post_everything.status_code, 302)
            self.assertEquals(success_post_everything.location, 'http://localhost/beacon/')
            self.assertEquals(len(outbox), 4)
            self.assertEquals(Vendor.query.count(), 2)
            self.assertEquals(len(Vendor.query.all()[1].categories), 5)
            self.assert_flashes('Thank you for signing up! Check your email for more information', 'alert-success')

            # successful post with existing email should update the profile, not send message
            success_post_old_email = self.client.post('/beacon/signup', data={
                'email': 'foo2@foo.com',
                'business_name': 'foo',
                'subcategories-1': 'on',
                'subcategories-2': 'on',
                'subcategories-3': 'on',
                'categories': 'Apparel'
            })

            self.assertEquals(success_post_old_email.status_code, 302)
            self.assertEquals(success_post_old_email.location, 'http://localhost/beacon/')
            self.assertEquals(len(outbox), 4)
            self.assertEquals(Vendor.query.count(), 2)
            self.assertEquals(len(Vendor.query.all()[1].categories), 5)
            self.assert_flashes(
                "You are already signed up! Your profile was updated with this new information", 'alert-info'
            )

            admin_mail, vendor_mail = 0, 0
            for _mail in outbox:
                if 'new vendor has signed up on beacon' in _mail.subject:
                    admin_mail += 1
                if 'Thank you for signing up' in _mail.subject:
                    vendor_mail += 1

            self.assertEquals(admin_mail, 2)
            self.assertEquals(vendor_mail, 2)

            with self.client.session_transaction() as session:
                assert 'email' in session
                assert 'business_name' in session
                self.assertEquals(session['email'], 'foo2@foo.com')
                self.assertEquals(session['business_name'], 'foo')

    def test_manage_subscriptions(self):
        '''Test subscription and unsubscription management
        '''

        self.client.post('/beacon/signup', data={
            'email': 'foo2@foo.com',
            'business_name': 'foo',
            'subcategories-1': 'on',
            'subcategories-2': 'on',
            'subcategories-3': 'on',
            'categories': 'Apparel'
        })

        manage = self.client.post('/beacon/manage', data=dict(
            email='foo2@foo.com'
        ))

        self.assert200(manage)
        form = self.get_context_variable('form')
        self.assertEquals(len(form.categories.choices), 3)

        # it shouldn't unsubscribe you if you click the wrong button
        not_unsub_button = self.client.post('/beacon/manage', data=dict(
            email='foo2@foo.com',
            categories=[1, 2],
        ))

        self.assert200(not_unsub_button)
        form = self.get_context_variable('form')
        self.assertEquals(len(form.categories.choices), 3)

        unsubscribe = self.client.post('/beacon/manage', data=dict(
            email='foo2@foo.com',
            categories=[1, 2],
            button='Update email preferences'
        ))

        self.assert200(unsubscribe)
        form = self.get_context_variable('form')
        self.assertEquals(len(form.categories.choices), 1)

        # it shouldn't matter if you somehow unsubscribe from things
        # you are accidentally subscribed to
        unsubscribe_all = self.client.post('/beacon/manage', data=dict(
            email='foo2@foo.com',
            categories=[3, 5, 6],
            button='Update email preferences'
        ))

        self.assert200(unsubscribe_all)
        self.assertTrue('You are not subscribed to anything!' in unsubscribe_all.data)
