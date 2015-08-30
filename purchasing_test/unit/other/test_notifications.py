# -*- coding: utf-8 -*-

from unittest import TestCase
from mock import patch, Mock, MagicMock
from purchasing.notifications import Notification

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
        self.assertEquals(notification.attachments, [])

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

    @patch('purchasing.notifications.render_template', return_value='a test')
    def test_notification_build_multi(self, render_template):
        '''Test multi builds multiple message objects
        '''
        notification = Notification(to_email=['foobar@foo.com', 'foobar2@foo.com'], from_email='foo@foo.com')

        notification.build_msg = Mock()
        notification.build_msg.return_value = []

        # should build two messages on multi send
        notification.send(multi=True)
        self.assertTrue(notification.build_msg.called)
        self.assertEquals(notification.build_msg.call_count, 2)

    @patch('purchasing.notifications.render_template', return_value='a test')
    def test_notification_build_single(self, render_template):
        '''Test non-multi only builds one message even with multiple emails
        '''
        notification = Notification(to_email=['foobar@foo.com', 'foobar2@foo.com'], from_email='foo@foo.com')

        notification.build_msg = Mock()
        notification.build_msg.return_value = []

        # should build two messages on multi send
        notification.send(multi=False)
        self.assertTrue(notification.build_msg.called)
        self.assertEquals(notification.build_msg.call_count, 1)
