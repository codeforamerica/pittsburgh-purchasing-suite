# -*- coding: utf-8 -*-

import datetime

from purchasing.database import Model, RefreshSearchViewMixin, Column

from purchasing.app import db
from purchasing_test.test_base import BaseTestCase
from purchasing_test.util import (
    insert_a_company, insert_a_user, get_a_role
)

from purchasing_test.factories import ContractTypeFactory, ContractBaseFactory, ContractPropertyFactory

from purchasing.data.contracts import LineItem

class TestscoutSearch(BaseTestCase):
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
        self.company_1 = insert_a_company(name='ship', insert_contract=False)
        company_2 = insert_a_company(name='boat', insert_contract=False)

        contract_type = ContractTypeFactory.create(name='test')
        self.contract_type2 = ContractTypeFactory.create(name='test2')

        self.contract1 = ContractBaseFactory.create(
            description='vessel', companies=[company_2], line_items=[LineItem(description='NAVY')],
            expiration_date=datetime.datetime.today() + datetime.timedelta(1), is_archived=False,
            financial_id='123', contract_type=contract_type
        )
        ContractBaseFactory.create(
            description='sail', financial_id='456', companies=[self.company_1],
            line_items=[LineItem(description='sunfish')], is_archived=False,
            expiration_date=datetime.datetime.today() + datetime.timedelta(1),
            contract_type=contract_type
        )
        ContractBaseFactory.create(
            description='sunfish', financial_id='789',
            properties=[ContractPropertyFactory.create(key='foo', value='engine')],
            expiration_date=datetime.datetime.today() + datetime.timedelta(1), is_archived=False,
            contract_type=contract_type
        )
        ContractBaseFactory.create(
            description='sunfish', financial_id='012',
            properties=[ContractPropertyFactory.create(key='foo', value='engine')],
            expiration_date=datetime.datetime.today() - datetime.timedelta(1), is_archived=False,
            contract_type=self.contract_type2
        )

        # db.session.execute('''
        #     REFRESH MATERIALIZED VIEW CONCURRENTLY search_view
        # ''')
        db.session.commit()

    def tearDown(self):
        db.session.execute('''DROP SCHEMA IF EXISTS public cascade;''')
        db.session.execute('''CREATE SCHEMA public;''')
        db.session.commit()
        db.session.remove()
        db.drop_all()
        db.get_engine(self.app).dispose()

    def test_search(self):
        db.session.execute('''
            REFRESH MATERIALIZED VIEW CONCURRENTLY search_view
        ''')
        db.session.commit()

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

        # make sure that contract types are properly handled
        self.assert200(self.client.get('/scout/search?archived=y&contract_type={}&q='.format(self.contract_type2.id)))
        self.assertEquals(len(self.get_context_variable('results')), 1)

class FakeModel(RefreshSearchViewMixin, Model):
    __tablename__ = 'fakefake'
    __table_args__ = {'extend_existing': True}

    id = Column(db.Integer, primary_key=True)
    description = Column(db.String(255))

    def __init__(self, *args, **kwargs):
        super(FakeModel, self).__init__(*args, **kwargs)

    @classmethod
    def record_called(cls):
        cls.called = True

    @classmethod
    def reset_called(cls):
        cls.called = False

    @classmethod
    def event_handler(cls, *args, **kwargs):
        return cls.record_called()

class TestEventHandler(BaseTestCase):
    def setUp(self):
        super(TestEventHandler, self).setUp()
        FakeModel.reset_called()

    def test_init(self):
        self.assertFalse(FakeModel.called)

    def test_create(self):
        FakeModel.create(description='abcd')
        self.assertTrue(FakeModel.called)

    def test_update(self):
        fake_model = FakeModel.create(description='abcd')
        FakeModel.reset_called()
        self.assertFalse(FakeModel.called)
        fake_model.update(description='efgh')
        self.assertTrue(FakeModel.called)

    def test_delete(self):
        fake_model = FakeModel.create(description='abcd')
        FakeModel.reset_called()
        self.assertFalse(FakeModel.called)
        fake_model.delete()
        self.assertTrue(FakeModel.called)
