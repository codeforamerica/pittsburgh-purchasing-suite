# -*- coding: utf-8 -*-

from flask import current_app
from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import insert_a_user, insert_a_role

class TestSherpa(BaseTestCase):

    def setUp(self):
        super(TestSherpa, self).setUp()
        self.staff_role = insert_a_role('staff')
        self.email = 'foo@foo.com'
        self.user = insert_a_user(email=self.email, role=self.staff_role)

    def test_sherpa(self):
        '''
        Checks that Sherpa endpoints return 200 success codes use correct templates.
        '''
        self.login_user(self.user)

        for rule in current_app.url_map.iter_rules():

            _endpoint = rule.endpoint.split('.')
            # filters out non-sherpa endpoints

            if (len(_endpoint) > 1 and _endpoint[1] == 'static') or _endpoint[0] != 'sherpa':
                continue
            else:
                response = self.client.get(rule.rule)
                self.assert200(response)
                self.assert_template_used(['sherpa/question.html', 'sherpa/termination.html'])
