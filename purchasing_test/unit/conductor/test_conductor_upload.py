# -*- coding: utf-8 -*-

from collections import defaultdict
from os import mkdir, rmdir
from shutil import rmtree
from flask import current_app, render_template
from werkzeug.datastructures import FileStorage, Headers
from cStringIO import StringIO

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_role, insert_a_user
)
from purchasing.data.contracts import get_all_contracts
from purchasing.data.companies import get_all_companies
from purchasing.data.models import LineItem, ContractBase

class TestCostarsUpload(BaseTestCase):

    def create_file(self, filename, content_type):
        headers = Headers()
        headers.add('Content-Type', content_type)
        return FileStorage(StringIO('test,this,csv'), filename=filename, headers=headers)

    def setUp(self):
        super(TestCostarsUpload, self).setUp()

        try:
            mkdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            rmtree(current_app.config.get('UPLOAD_DESTINATION'))
            mkdir(current_app.config.get('UPLOAD_DESTINATION'))

        self.conductor_role_id = insert_a_role('conductor')
        self.conductor = insert_a_user(role=self.conductor_role_id, email='conductor@foo.com')

        self.admin_role_id = insert_a_role('admin')
        self.admin = insert_a_user(role=self.admin_role_id, email='admin@foo.com')

        self.superadmin_role_id = insert_a_role('superadmin')
        self.superadmin = insert_a_user(role=self.superadmin_role_id, email='superadmin@foo.com')

        self.staff_role_id = insert_a_role('staff')
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role_id)

    def tearDown(self):
        super(TestCostarsUpload, self).tearDown()
        # clear out the uploads folder
        rmtree(current_app.config.get('UPLOAD_DESTINATION'))
        try:
            rmdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            pass

    def test_page_locked(self):
        '''Test page won't render for people without proper roles
        '''
        # test that you can't access upload page unless you are signed in with proper role
        self.assertEqual(self.client.get('/conductor/upload/costars').status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        for user in [self.conductor, self.admin, self.superadmin]:
            self.login_user(user)
            self.assert200(self.client.get('/conductor/upload/costars'))

    def test_upload_locked(self):
        '''Test upload doesn't work without proper role
        '''
        test_file = self.create_file('costars-99.csv', 'text/csv')
        upload_csv = self.client.post('/conductor/upload/costars', data=dict(upload=test_file))
        self.assertEqual(upload_csv.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        for user in [self.conductor, self.admin, self.superadmin]:
            self.login_user(user)
            test_file = self.create_file('costars-99.csv', 'text/csv')
            req = self.client.post('/conductor/upload/costars', follow_redirects=True, data=dict(upload=test_file))
            self.assertTrue(req.data.count('Upload processing...'), 1)

    def test_upload_validation(self):
        '''Test that only csv's can be uploaded
        '''
        self.login_user(self.conductor)

        txt_file = self.create_file('test.txt', 'text/plain')
        upload_txt = self.client.post('conductor/upload/costars', data=dict(upload=txt_file))
        self.assertTrue(upload_txt.data.count('.csv files only'), 1)

        csv_file = self.create_file('test.csv', 'text/csv')
        upload_csv = self.client.post('conductor/upload/costars', data=dict(upload=csv_file))
        self.assertEquals(upload_csv.location, 'http://localhost/conductor/upload/costars/processing')

    def test_upload_success(self):
        '''Test that file upload works and updates database
        '''
        self.login_user(self.conductor)
        costars_filepath = current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/COSTARS-1.csv'
        costars_filename = 'COSTARS-1.csv'
        props = defaultdict(list)

        self.client.post(
            'conductor/upload/costars/_process',
            data=dict(filepath=costars_filepath, filename=costars_filename, _delete=False)
        )

        contracts = get_all_contracts()
        # assert we got both contracts
        self.assertEquals(len(contracts), 3)

        for contract in contracts:
            self.assertTrue(contract.expiration_date is not None)
            for property in contract.properties:
                props[property.key].append(property.value)

        # assert the county importer works properly
        self.assertEquals(len(props['Located in']), 2)
        self.assertEquals(len(props['List of manufacturers']), 2)

        # assert that we got all the line items
        self.assertEquals(LineItem.query.count(), 12)

        companies = get_all_companies()

        self.assertEquals(len(companies), 3)
        for company in companies:
            self.assertEquals(company.contacts.count(), 0)

class TestCostarsContractUpload(TestCostarsUpload):
    def setUp(self):
        super(TestCostarsContractUpload, self).setUp()

        self.login_user(self.conductor)
        costars_filepath = current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/COSTARS-1.csv'
        costars_filename = 'COSTARS-1.csv'

        self.client.post(
            'conductor/upload/costars/_process',
            data=dict(filepath=costars_filepath, filename=costars_filename, _delete=False)
        )
        self.logout_user()

    def tearDown(self):
        super(TestCostarsContractUpload, self).tearDown()

    def test_app_locked(self):
        '''Test that the views are gated
        '''
        self.assertEquals(self.client.get('/conductor/upload/costars/contracts').status_code, 302)
        self.assertEquals(self.client.post('/conductor/upload/costars/contracts').status_code, 302)

    def test_contract_upload_view(self):
        '''Test the upload contract views work as expected
        '''
        self.login_user(self.admin)
        self.assert200(self.client.get('/conductor/upload/costars/contracts'))
        self.assertEquals(len(self.get_context_variable('contracts')), 3)

    def test_contract_upload(self):
        '''Test that uploading contracts work as expected
        '''
        self.login_user(self.admin)
        test_file = self.create_file('test.pdf', 'application/pdf')
        self.client.post(
            '/conductor/upload/costars/contracts',
            data=dict(upload=test_file, contract_id=1)
        )
        self.assertTrue(ContractBase.query.get(1).contract_href is not None)
        self.assert200(self.client.get('/conductor/upload/costars/contracts'))
        self.assertEquals(len(self.get_context_variable('contracts')), 2)
