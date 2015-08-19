# -*- coding: utf-8 -*-

import datetime

from purchasing.app import db
from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_company, insert_a_contract,
    insert_a_user, get_a_role
)

from purchasing.data.models import LineItem

class TestWexplorerSearch(BaseTestCase):
    render_templates = True

    def setUp(self):
        from flask_migrate import upgrade
        upgrade()

        # insert the users/roles
        self.admin_role = get_a_role('admin')
        self.superadmin_role = get_a_role('superadmin')
        self.admin_user = insert_a_user(email='foo@foo.com', role=self.admin_role)
        self.superadmin_user = insert_a_user(email='bar@foo.com', role=self.superadmin_role)

        # insert the companies/contracts
        company_1 = insert_a_company(name='ship', insert_contract=False)
        company_2 = insert_a_company(name='boat', insert_contract=False)

        insert_a_contract(
            description='vessel', companies=[company_2], line_items=[LineItem(description='NAVY')],
            expiration_date=datetime.datetime.today() + datetime.timedelta(1), is_archived=False,
            financial_id='123'
        )
        insert_a_contract(
            description='sail', financial_id='456', companies=[company_1],
            line_items=[LineItem(description='sunfish')], is_archived=False,
            expiration_date=datetime.datetime.today() + datetime.timedelta(1)
        )
        insert_a_contract(
            description='sunfish', financial_id='789', properties=[dict(key='foo', value='engine')],
            expiration_date=datetime.datetime.today() + datetime.timedelta(1), is_archived=False
        )
        insert_a_contract(
            description='sunfish', financial_id='012', properties=[dict(key='foo', value='engine')],
            expiration_date=datetime.datetime.today() - datetime.timedelta(1), is_archived=False
        )

    def tearDown(self):
        db.session.execute('''DROP SCHEMA IF EXISTS public cascade;''')
        db.session.execute('''CREATE SCHEMA public;''')
        db.session.commit()
        db.session.remove()
        db.drop_all()
        db.get_engine(self.app).dispose()

    def test_search(self):
        '''Check searches return properly: descriptions, names, properties, line items, financial ids
        '''
        self.assert200(self.client.get('/scout/search?q=ship'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=boat'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=vessel'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=FAKEFAKEFAKE'))
        self.assertEquals(len(self.get_context_variable('results')), 0)

        self.assert200(self.client.get('/scout/search?q=sunfish'))
        self.assertEquals(len(self.get_context_variable('results')), 2)

        # make sure you can filter with the check boxes
        self.assert200(self.client.get('/scout/search?q=sunfish&line_item=y'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=engine'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        self.assert200(self.client.get('/scout/search?q=123'))
        self.assertEquals(len(self.get_context_variable('results')), 1)

        # check searching for everything gives you everything
        self.assert200(self.client.get('/scout/search?q='))
        self.assertEquals(len(self.get_context_variable('results')), 3)

        # make sure that crazy input still returns a 200
        self.assert200(self.client.get('/scout/search?q=fj02jf,/fj20j8**#*U!?JX&&'))
        self.assert200(self.client.get('/scout/search?q=super+man'))

        # make sure that archived contracts are properly handled
        self.assert200(self.client.get('/scout/search?archived=y&q='))
        self.assertEquals(len(self.get_context_variable('results')), 4)
