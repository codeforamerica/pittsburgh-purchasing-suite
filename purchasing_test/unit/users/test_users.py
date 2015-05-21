# -*- coding: utf-8 -*-

from mock import Mock, patch
from flask.ext.login import login_user

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import insert_a_user, insert_a_role
from purchasing.users.models import User

class TestUserAuth(BaseTestCase):
    render_template = True

    def setUp(self):
        super(TestUserAuth, self).setUp()
        self.email = 'foo@foo.com'
        insert_a_user(email=self.email)

    def test_login_route(self):
        '''
        Test the login route works propertly
        '''
        request = self.client.get('/users/login')
        self.assert200(request)
        self.assert_template_used('users/login.html')
        # test that new users are anonymous
        self.assertTrue(self.get_context_variable('current_user').is_anonymous())

    def test_thispage(self):
        '''
        Test the thispage utility properly populates
        '''
        request = self.client.get('/about', follow_redirects=True)
        self.assertTrue('?next=%2Fabout%2F' in request.data)

    @patch('urllib2.urlopen')
    def test_auth_persona_failure(self, urlopen):
        '''
        Test that we reject when persona throws bad statuses to us
        '''
        mock_open = Mock()
        mock_open.read.side_effect = ['{"status": "error"}']
        urlopen.return_value = mock_open

        post = self.client.post('/users/auth', data=dict(
            assertion='test'
        ))

        self.assert403(post)

    @patch('urllib2.urlopen')
    def test_auth_no_user(self, urlopen):
        '''
        Test that we reject bad email addresses
        '''
        mock_open = Mock()
        mock_open.read.side_effect = ['{"status": "okay", "email": "not_a_valid_email"}']
        urlopen.return_value = mock_open

        post = self.client.post('/users/auth', data=dict(
            assertion='test'
        ))

        self.assert403(post)

    @patch('urllib2.urlopen')
    def test_auth_success(self, urlopen):
        '''
        Test that we properly login users
        '''
        mock_open = Mock()
        mock_open.read.side_effect = [
            '{"status": "okay", "email": "' + self.email + '"}',
            '{"status": "okay", "email": "' + self.email + '"}'
        ]
        urlopen.return_value = mock_open

        post = self.client.post('/users/auth?next=/explore/', data=dict(
            assertion='test'
        ))

        self.assert200(post)
        self.assertEquals(post.data, '/explore/')

        self.client.get('/users/logout')

    @patch('urllib2.urlopen')
    def test_new_user_success(self, urlopen):
        '''
        Test that we properly register and onboard new users with a city domain
        '''
        # insert all of our roles
        insert_a_role('superadmin')
        insert_a_role('admin')
        insert_a_role('staff')

        # assert we have only one user
        self.assertEquals(User.query.count(), 1)

        mock_open = Mock()
        mock_open.read.side_effect = [
            '{"status": "okay", "email": "new@foo.com"}'
        ]
        urlopen.return_value = mock_open

        post = self.client.post('/users/auth?next=/explore/', data=dict(
            assertion='test'
        ))

        # assert we add a new user and redirect to the register page
        self.assertEquals(User.query.count(), 2)
        self.assertEquals(post.status_code, 200)
        self.assertEquals(post.data, '/users/profile')

        # assert we get the new user message
        register = self.client.get('/users/profile')
        self.assertTrue('Welcome to the Pittsbugh Purchasing Suite!' in register.data)
        self.assert_template_used('users/profile.html')

        # assert that you cannot update with junk information
        bad_update = self.client.post('/users/profile', data=dict(
            department='THIS IS NOT A VALID DEPARTMENT'
        ), follow_redirects=True)
        self.assertFalse(User.query.get(2).department == 'THIS IS NOT A VALID DEPARTMENT')
        self.assertTrue('Not a valid choice' in bad_update.data)

        # update the user successfully
        update = self.client.post('/users/profile', data=dict(
            first_name='foo', last_name='bar', department='Other'
        ))

        # assert we successfully update
        self.assertEquals(update.status_code, 302)
        self.assertEquals(update.location, 'http://localhost/users/profile')
        self.assert_flashes('Updated your profile!', 'alert-success')

        # make sure the new user message is gone
        updated = self.client.get('/users/profile')

        self.assertTrue('Welcome to the Pittsbugh Purchasing Suite!' not in updated.data)
        self.assert_template_used('users/profile.html')

    @patch('urllib2.urlopen')
    def test_logout(self, urlopen):
        '''
        Test that we can logout properly
        '''

        login_user(User.query.all()[0])

        logout = self.client.get('/users/logout', follow_redirects=True)
        self.assertTrue('Logged out successfully' in logout.data)
        self.assert_template_used('users/logout.html')

        login_user(User.query.all()[0])
        logout = self.client.post('/users/logout?persona=True', follow_redirects=True)
        self.assertTrue(logout.data, 'OK')
