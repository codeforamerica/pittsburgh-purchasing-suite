# -*- coding: utf-8 -*-

from flask.ext.testing import TestCase

from purchasing.settings import TestConfig
from purchasing.app import create_app as _create_app, db

class BaseTestCase(TestCase):
    '''
    A base test case that boots our app
    '''
    def create_app(self):
        return _create_app(TestConfig)

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.get_engine(self.app).dispose()

    def assert_flashes(self, expected_message, expected_category='message'):
        '''
        Helper to test if we have flashes.
        Taken from: http://blog.paulopoiati.com/2013/02/22/testing-flash-messages-in-flask/
        '''
        with self.client.session_transaction() as session:
            try:
                category, message = session['_flashes'][0]
            except KeyError:
                raise AssertionError('nothing flashed')
            assert expected_message in message
            assert expected_category == category
