# -*- coding: utf-8 -*-

import json
from flask import current_app

from purchasing.extensions import mail
from purchasing_test.unit.test_base import BaseTestCase
from purchasing.data.importer.nigp import main

class TestOpportunities(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestOpportunities, self).setUp()
        # import our test categories
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

    def test_index(self):
        response = self.client.get('/opportunities/')
        self.assert200(response)
        self.assert_template_used('opportunities/index.html')

    def test_signup(self):
        response = self.client.get('/opportunities/signup')
        self.assert200(response)
        subcats = json.loads(self.get_context_variable('subcategories'))

        # assert two categories
        self.assertEquals(len(subcats.keys()), 2)
        # assert five total subcatgories
        self.assertEquals(len([item for sublist in subcats.values() for item in sublist]), 5)

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
            success_post = self.client.post('/opportunities/signup', data=dict(
                email='foo@foo.com',
                business_name='foo',
                subcategories=[1],
                categories='Apparel'
            ))

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/opportunities/')
            self.assertEquals(len(outbox), 1)
            self.assert_flashes('Thank you for signing up! Check your email for more information', 'alert-success')

            # successful post with two sets of subcategories
            success_post_everything = self.client.post('/opportunities/signup', data=dict(
                email='foo2@foo.com',
                business_name='foo',
                subcategories=[1, 2, 3, 4, 5],
                categories='Apparel'
            ))

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/opportunities/')
            self.assertEquals(len(outbox), 2)
            self.assert_flashes('Thank you for signing up! Check your email for more information', 'alert-success')

            # successful post with existing email should update the profile, not send message
            success_post_old_email = self.client.post('/opportunities/signup', data=dict(
                email='foo@foo.com',
                business_name='foo',
                subcategories=[1, 2, 3],
                categories='Apparel'
            ))

            self.assertEquals(success_post.status_code, 302)
            self.assertEquals(success_post.location, 'http://localhost/opportunities/')
            self.assertEquals(len(outbox), 2)
            self.assert_flashes("You are already signed up! Your profile was updated with this new information", 'alert-info')
