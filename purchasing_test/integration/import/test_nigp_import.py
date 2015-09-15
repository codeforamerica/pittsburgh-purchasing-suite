# -*- coding: utf-8 -*-

from flask import current_app
from purchasing_test.test_base import BaseTestCase

from purchasing.data.importer.nigp import main
from purchasing.opportunities.models import Category

class TestNigpImport(BaseTestCase):
    def test_nigp_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

        categories = Category.query.all()

        self.assertEquals(len(categories), 5)
