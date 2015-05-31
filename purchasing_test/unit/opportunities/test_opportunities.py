# -*- coding: utf-8 -*-

import json
from flask import current_app

from purchasing.extensions import mail
from purchasing_test.unit.test_base import BaseTestCase
from purchasing.data.importer.nigp import main
from purchasing.opportunities.models import Vendor

class TestOpportunities(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestOpportunities, self).setUp()
        # import our test categories
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

    def test_index(self):
        '''
        Index page works as expected
        '''
        response = self.client.get('/opportunities/')
        self.assert200(response)
        self.assert_template_used('opportunities/index.html')

        # assert clicking signup works as expected
        signup = self.client.post('/opportunities/signup?email=foo@foo.com', follow_redirects=True)
        self.assertTrue('foo@foo.com' in signup.data)

    def test_signup(self):
        '''
        Signups work as expected including validation errors, signups, etc.
        '''
        response = self.client.get('/opportunities/signup')
        self.assert200(response)
        subcats = json.loads(self.get_context_variable('subcategories'))

        # assert two categories (plus the total category)
        self.assertEquals(len(subcats.keys()), 3)
        # assert five total subcatgories (plus 5 in the total field)
        self.assertEquals(len([item for sublist in subcats.values() for item in sublist]), 10)

        # assert email, business, categories needed
        no_email_post = self.client.post('/opportunities/signup', data=dict(
            first_name='foo'
        ))

        self.assert200(no_email_post)
        self.assertTrue(no_email_post.data.count('alert-danger'), 3)
        # ensure that there are two required field notes
        self.assertTrue(no_email_post.data.count('This field is required'), 2)

        # assert valid email address
        invalid_email_post = self.client.post('/opportunities/signup', data=dict(
            email='INVALID',
            business_name='test',
            subcategories=[1]
        ))

        self.assert200(invalid_email_post)
        self.assertTrue(invalid_email_post.data.count('alert-danger'), 1)
        self.assertTrue(invalid_email_post.data.count('Invalid email address.'), 1)

        # assert valid categories
        invalid_category_post = self.client.post('/opportunities/signup', data=dict(
            email='foo@foo.com',
            business_name='test',
            subcategories=[999]
        ))

        self.assert200(invalid_category_post)
        self.assertTrue(invalid_category_post.data.count('alert-danger'), 1)
        self.assertTrue('999 is not a valid choice!' in invalid_category_post.data)

        with mail.record_messages() as outbox:

            # successful post with only one set of subcategories
            success_post = self.client.post('/opportunities/signup', data={
                'email': 'foo@foo.com',
                'business_name': 'foo',
                'subcategories-1': 'on',
                'categories': 'Apparel'
            })

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/opportunities/')
            self.assertEquals(len(outbox), 1)
            self.assertEquals(Vendor.query.count(), 1)
            self.assertEquals(len(Vendor.query.first().categories), 1)
            self.assert_flashes('Thank you for signing up! Check your email for more information', 'alert-success')

            # successful post with two sets of subcategories
            success_post_everything = self.client.post('/opportunities/signup', data={
                'email': 'foo2@foo.com',
                'business_name': 'foo',
                'subcategories-1': 'on',
                'subcategories-2': 'on',
                'subcategories-3': 'on',
                'subcategories-4': 'on',
                'subcategories-5': 'on',
                'categories': 'Apparel'
            })

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/opportunities/')
            self.assertEquals(len(outbox), 2)
            self.assertEquals(Vendor.query.count(), 2)
            self.assertEquals(len(Vendor.query.all()[1].categories), 5)
            self.assert_flashes('Thank you for signing up! Check your email for more information', 'alert-success')

            # successful post with existing email should update the profile, not send message
            success_post_old_email = self.client.post('/opportunities/signup', data={
                'email': 'foo2@foo.com',
                'business_name': 'foo',
                'subcategories-1': 'on',
                'subcategories-2': 'on',
                'subcategories-3': 'on',
                'categories': 'Apparel'
            })

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/opportunities/')
            self.assertEquals(len(outbox), 2)
            self.assertEquals(Vendor.query.count(), 2)
            self.assertEquals(len(Vendor.query.all()[1].categories), 3)
            self.assert_flashes("You are already signed up! Your profile was updated with this new information", 'alert-info')

    def test_manage_subscriptions(self):
        '''
        Test subscription and unsubscription management
        '''

        subscribe = self.client.post('/opportunities/signup', data={
            'email': 'foo2@foo.com',
            'business_name': 'foo',
            'subcategories-1': 'on',
            'subcategories-2': 'on',
            'subcategories-3': 'on',
            'categories': 'Apparel'
        })

        manage = self.client.post('/opportunities/manage', data=dict(
            email='foo2@foo.com'
        ))

        self.assert200(manage)
        form = self.get_context_variable('form')
        self.assertEquals(len(form.subscriptions.choices), 3)

        # it shouldn't unsubscribe you if you click the wrong button
        not_unsub_button = self.client.post('/opportunities/manage', data=dict(
            email='foo2@foo.com',
            subscriptions=[1, 2],
        ))

        self.assert200(not_unsub_button)
        form = self.get_context_variable('form')
        self.assertEquals(len(form.subscriptions.choices), 3)

        unsubscribe = self.client.post('/opportunities/manage', data=dict(
            email='foo2@foo.com',
            subscriptions=[1, 2],
            button='Unsubscribe from Checked'
        ))

        self.assert200(unsubscribe)
        form = self.get_context_variable('form')
        self.assertEquals(len(form.subscriptions.choices), 1)

        # it shouldn't matter if you somehow unsubscribe from things
        # you are accidentally subscribed to
        unsubscribe_all = self.client.post('/opportunities/manage', data=dict(
            email='foo2@foo.com',
            subscriptions=[3, 5, 6],
            button='Unsubscribe from Checked'
        ))

        self.assert200(unsubscribe_all)
        self.assertTrue('You are not subscribed to anything!' in unsubscribe_all.data)
