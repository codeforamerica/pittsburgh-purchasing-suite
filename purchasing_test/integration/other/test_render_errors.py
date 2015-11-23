# -*- coding: utf-8 -*-

from flask import abort
from purchasing.public.models import AppStatus
from purchasing_test.test_base import BaseTestCase

class TestRenderErrors(BaseTestCase):
    render_templates = True

    def build_rule(self, code):
        def rule():
            abort(code)
        return rule

    def setUp(self):
        super(TestRenderErrors, self).setUp()
        AppStatus.create()
        self.codes = [401, 403, 404, 413, 500]

        for i in self.codes:
            self.client.application.add_url_rule(
                '/' + str(i), str(i), self.build_rule(i)
            )

    def test_render_errors(self):
        for i in self.codes:
            self.client.get('/' + str(i))
            self.assert_template_used('errors/{}.html'.format(i))
