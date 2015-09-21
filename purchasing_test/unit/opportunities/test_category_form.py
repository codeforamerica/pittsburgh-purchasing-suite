# -*- coding: utf-8 -*-

import json
import os
from flask import current_app
from flask_testing import TestCase

from purchasing.app import create_app as _create_app

from purchasing.opportunities.forms import CategoryForm
from purchasing_test.factories import CategoryFactory

class TestCategoryForm(TestCase):
    def create_app(self):
        os.environ['CONFIG'] = 'purchasing.settings.TestConfig'
        return _create_app()

    def setUp(self):
        self.category1 = CategoryFactory.build(category='one', category_friendly_name='One')
        self.category2 = CategoryFactory.build(category='one', category_friendly_name='Two')
        self.category3 = CategoryFactory.build(category='ten', category_friendly_name='Ten')
        self.category4 = CategoryFactory.build(category='ten', category_friendly_name='Eleven')
        self.all_categories = [
            self.category1, self.category2, self.category3, self.category4
        ]

    def test_build_categories(self):
        with current_app.test_request_context():
            new_form = CategoryForm()
            subcats = new_form.build_categories(self.all_categories)
            self.assertEquals(len(subcats), 3)
            self.assertEquals(len(subcats['Select All']), 4)

    def test_display_cleanup(self):
        with current_app.test_request_context():
            new_form = CategoryForm()
            self.assertFalse(hasattr(new_form, '_categories'))
            self.assertFalse(hasattr(new_form, '_subcategories'))
            new_form.display_cleanup(all_categories=self.all_categories)
            self.assertTrue(hasattr(new_form, '_categories'))
            self.assertTrue(hasattr(new_form, '_subcategories'))

            categories = json.loads(new_form.get_categories())
            self.assertEquals(len(categories), 2)
            self.assertTrue('one' in categories)
            self.assertTrue('ten' in categories)

            subcategories = json.loads(new_form.get_subcategories())
            self.assertEquals(len(subcategories), 3)
