# -*- coding: utf-8 -*-

import os

from mock import Mock, patch
from flask.ext.testing import TestCase as FlaskTestCase

from purchasing.settings import TestConfig
from purchasing.app import create_app as _create_app, db

import logging
logging.getLogger("factory").setLevel(logging.WARN)

class BaseTestCase(FlaskTestCase):
    '''
    A base test case that boots our app
    '''
    def create_app(self):
        os.environ['CONFIG'] = 'purchasing.settings.TestConfig'
        return _create_app()

    def setUp(self):
        db.create_all()
        self.app.config['CELERY_ALWAYS_EAGER'] = True
        self.app.config['BROKER_BACKEND'] = 'memory'
        self.app.config['CELERY_EAGER_PROPAGATES_EXCEPTIONS'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.get_engine(self.app).dispose()

    def assertTemplatesUsed(self, names, tmpl_name_attribute='name'):
        '''
        Subclass assertTemplateUsed from the flask-testing TestCase to
        allow for multiple templates
        '''
        if isinstance(names, basestring):
            names = [names]

        used_templates = []

        for template, context in self.templates:
            if getattr(template, tmpl_name_attribute) in names:
                return True

            used_templates.append(template.name)

        raise AssertionError("template %s not used. Templates were used: %s" % (names, ' '.join(used_templates)))

    assert_template_used = assertTemplatesUsed

    def assert_flashes(self, expected_message, expected_category='message'):
        '''
        Helper to test if we have flashes.
        Taken from: http://blog.paulopoiati.com/2013/02/22/testing-flash-messages-in-flask/
        '''
        with self.client.session_transaction() as session:
            messages, categories = [], []
            try:
                flashes = session['_flashes']
                for flash in flashes:
                    categories.append(flash[0])
                    messages.append(flash[1])
            except KeyError:
                raise AssertionError('nothing flashed')
            assert expected_message in messages
            assert expected_category in categories

    @patch('urllib2.urlopen')
    def login_user(self, user, urlopen):
        _email = user.email if user else 'foo@foo.com'
        mock_open = Mock()
        mock_open.read.side_effect = ['{"status": "okay", "email": "' + _email + '"}']
        urlopen.return_value = mock_open

        self.client.post('/users/auth', data=dict(
            assertion='test'
        ))

    def logout_user(self):
        self.client.post('/users/logout')
