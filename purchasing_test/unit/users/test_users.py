# -*- coding: utf-8 -*-

from mock import Mock, patch
from flask.ext.login import login_user

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import insert_a_user
from purchasing.users.models import User

class TestUserAuth(BaseTestCase):
    def setUp(self):
        super(TestUserAuth, self).setUp()
        self.email = 'foo@foo.com'
        insert_a_user(email=self.email)

    def test_login_route(self):
        request = self.client.get('/users/login')
        self.assert200(request)
        self.assert_template_used('users/login.html')
        # test that new users are anonymous
        self.assertTrue(self.get_context_variable('current_user').is_anonymous())

    def test_thispage(self):
        request = self.client.get('/about', follow_redirects=True)
        self.assertTrue('?next=%2Fabout%2F' in request.data)

    @patch('urllib2.urlopen')
    def test_auth_persona_failure(self, urlopen):
        mock_open = Mock()
        mock_open.read.side_effect = ['{"status": "error"}']
        urlopen.return_value = mock_open

        post = self.client.post('/users/auth', data=dict(
            assertion='test'
        ))

        self.assert403(post)

    @patch('urllib2.urlopen')
    def test_auth_no_user(self, urlopen):
        mock_open = Mock()
        mock_open.read.side_effect = ['{"status": "okay", "email": "not_a_valid_email"}']
        urlopen.return_value = mock_open

        post = self.client.post('/users/auth', data=dict(
            assertion='test'
        ))

        self.assert403(post)

    @patch('urllib2.urlopen')
    def test_auth_success(self, urlopen):
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
    def test_logout(self, urlopen):

        login_user(User.query.all()[0])

        logout = self.client.get('/users/logout', follow_redirects=True)
        self.assertTrue('Logged out successfully' in logout.data)
        self.assert_template_used('users/logout.html')

        login_user(User.query.all()[0])
        logout = self.client.post('/users/logout?persona=True', follow_redirects=True)
        self.assertTrue(logout.data, 'OK')
