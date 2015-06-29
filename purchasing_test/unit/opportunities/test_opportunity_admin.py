# -*- coding: utf-8 -*-

import datetime
from flask import current_app

from purchasing.opportunities.models import Opportunity, Vendor, RequiredBidDocument
from purchasing.data.importer.nigp import main

from unittest import skip
from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_role, insert_a_user, insert_a_document,
    insert_an_opportunity
)

class TestOpportunities(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestOpportunities, self).setUp()
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

        self.admin_role = insert_a_role('admin')
        self.staff_role = insert_a_role('staff')

        self.admin = insert_a_user(role=self.admin_role)
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role)

        self.document = insert_a_document()
        self.opportunity1 = insert_an_opportunity(
            contact_id=self.admin.id, created_by=self.staff.id, required_documents=[self.document]
        )
        self.opportunity2 = insert_an_opportunity(
            contact_id=self.admin.id, created_by=self.staff.id, required_documents=[self.document],
            is_public=True, planned_open=datetime.date.today() + datetime.timedelta(1),
            planned_deadline=datetime.date.today() + datetime.timedelta(2)
        )
        self.opportunity3 = insert_an_opportunity(
            contact_id=self.admin.id, created_by=self.staff.id, required_documents=[self.document],
            is_public=False, planned_open=datetime.date.today() - datetime.timedelta(2),
            planned_deadline=datetime.date.today() - datetime.timedelta(1)
        )

    @skip('TODO: write test for document upload')
    def test_document_upload(self):
        pass

    @skip('TODO: write test for opportunity building')
    def test_build_opportunity(self):
        pass

    def test_create_a_contract(self):
        '''Tests create contract page
        '''
        self.assertEquals(Opportunity.query.count(), 3)
        self.assertEquals(self.client.get('/beacon/opportunities/admin/new').status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin)
        self.assert200(self.client.get('/beacon/opportunities/admin/new'))

        # build data dictionaries
        bad_data = {
            'department': 'Other', 'contact_email': self.staff.email,
            'title': None, 'description': None, 'planned_open': datetime.date.today(),
            'planned_deadline': datetime.date.today() + datetime.timedelta(1),
            'is_public': False
        }

        # assert that you need a title & description
        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 3)
        self.assert200(new_contract)
        self.assertTrue('This field is required.' in new_contract.data)

        bad_data['title'] = 'Foo'
        bad_data['description'] = 'Bar'
        bad_data['planned_deadline'] = datetime.date.today() - datetime.timedelta(1)

        # assert you can't create a contract with an expired deadline
        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 3)
        self.assert200(new_contract)
        self.assertTrue('The deadline has to be after today!' in new_contract.data)

        bad_data['description'] = 'TOO LONG! ' * 500
        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 3)
        self.assert200(new_contract)
        self.assertTrue('Text cannot be more than 500 words!' in new_contract.data)

        bad_data['description'] = 'Just right.'
        bad_data['is_public'] = True
        bad_data['planned_deadline'] = datetime.date.today() + datetime.timedelta(1)

        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert_flashes('Opportunity Successfully Created!', 'alert-success')

    def test_edit_a_contract(self):
        '''Tests updating a contract
        '''
        self.assertEquals(self.client.get('/beacon/opportunities/2/admin/edit').status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin)
        self.assert200(self.client.get('/beacon/opportunities/2/admin/edit'))

        self.assert200(self.client.get('/beacon/opportunities'))

        self.assertEquals(len(self.get_context_variable('active')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 1)

        self.client.post('/beacon/opportunities/2/admin/edit', data={
            'planned_open': datetime.date.today(), 'title': 'Updated',
            'description': 'Updated Contract!', 'is_public': True
        })
        self.assert_flashes('Opportunity Successfully Updated!', 'alert-success')

        self.assert200(self.client.get('/beacon/opportunities'))
        self.assertEquals(len(self.get_context_variable('active')), 2)
        self.assertEquals(len(self.get_context_variable('upcoming')), 0)

    def test_browse_contract(self):
        '''Tests browse page loads properly
        '''
        # test admin view restrictions
        self.assert200(self.client.get('/beacon/opportunities'))
        self.assertEquals(len(self.get_context_variable('active')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 1)

        self.login_user(self.admin)
        self.assert200(self.client.get('/beacon/opportunities'))
        self.assertEquals(len(self.get_context_variable('active')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 1)
        self.assertEquals(Opportunity.query.count(), 3)

    def test_contract_detail(self):
        '''Tests individual contract opportunity pages
        '''
        self.assert200(self.client.get('/beacon/opportunities/1'))
        self.assert200(self.client.get('/beacon/opportunities/2'))
        self.assert404(self.client.get('/beacon/opportunities/999'))
