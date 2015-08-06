# -*- coding: utf-8 -*-

from unittest import TestCase
from mock import patch, MagicMock
from purchasing.notifications import Notification, render_template, current_app, mail

class TestNotification(TestCase):
    @patch('purchasing.notifications.render_template', return_value='a test')
    def test_notification_initialization(self, render_template):
        '''Test notifications properly initialize
        '''
        notification = Notification(from_email='foo@foo.com')
        self.assertEquals(notification.to_email, [])
        self.assertEquals(notification.from_email, 'foo@foo.com')
        self.assertEquals(notification.cc_email, [])
        self.assertEquals(notification.subject, '')
        self.assertEquals(notification.html_body, 'a test')
        self.assertEquals(notification.txt_body, '')

    @patch('purchasing.notifications.render_template', return_value='a test')
    def test_notification_flatten(self, render_template):
        '''Test notification kwarg flattener
        '''
        obj = MagicMock()
        obj.__unicode__ = lambda x: 'quux'
        notification = Notification(from_email='foo@foo.com', foo='bar', baz=['qux1', obj])
        self.assertEquals(
            {'foo': 'bar', 'baz': 'qux1; qux2'},
            notification.convert_models(dict(foo='bar', baz=['qux1', 'qux2']))
        )

    @patch('purchasing.notifications.render_template', return_value='a test')
    @patch('purchasing.notifications.current_app')
    @patch('purchasing.notifications.mail')
    def test_notification_send(self, render_template, current_app, mail):
        '''Test notification sender
        '''
        current_app.logger = MagicMock()
        mail.send = MagicMock()
        notification = Notification(to_email='foobar@foo.com', from_email='foo@foo.com')

        self.assertTrue(notification.send())

    @patch('purchasing.notifications.render_template', return_value='a test')
    def test_notification_reshape(self, render_template):
        '''Test notification recipient flattener
        '''
        notification = Notification(to_email='foobar@foo.com', from_email='foo@foo.com')
        test_recips = [('a',), ('multi',), ['nested', 'thing']]
        self.assertEquals(
            ['a', 'multi', 'nested', 'thing'],
            notification.flatten(test_recips)
        )

        test_recips_complex = ['a', ['b', ['c', 'd']], ['e']]
        self.assertEquals(
            ['a', 'b', 'c', 'd', 'e'],
            notification.flatten(test_recips_complex)
        )
