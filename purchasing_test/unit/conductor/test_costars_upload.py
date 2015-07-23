# -*- coding: utf-8 -*-

import unittest

from os import mkdir, listdir, rmdir
from shutil import rmtree
from flask import current_app
from werkzeug.datastructures import FileStorage
from cStringIO import StringIO

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_role, insert_a_user
)
from purchasing.conductor.views import upload as costars_upload
from purchasing.conductor.forms import FileUpload

class TestCostarsUpload(BaseTestCase):
    def setUp(self):
        super(TestCostarsUpload, self).setUp()

        self.conductor_role_id = insert_a_role('conductor')
        self.conductor = insert_a_user(role=self.conductor_role_id, email='conductor@foo.com')

        self.admin_role_id = insert_a_role('admin')
        self.admin = insert_a_user(role=self.admin_role_id, email='admin@foo.com')

        self.superadmin_role_id = insert_a_role('superadmin')
        self.superadmin = insert_a_user(role=self.superadmin_role_id, email='superadmin@foo.com')

        self.staff_role_id = insert_a_role('staff')
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role_id)

    def test_page_locked(self):
        '''Test page won't render for people without proper roles
        '''
        # test that you can't access upload page unless you are signed in with proper role
        request = self.client.get('/conductor/upload_new')
        self.assertEqual(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.conductor)
        self.assert200(self.client.get('/conductor/upload_new'))

        self.login_user(self.admin)
        self.assert200(self.client.get('/conductor/upload_new'))

        self.login_user(self.superadmin)
        self.assert200(self.client.get('/conductor/upload_new'))

    def test_upload_locked(self):
        '''Test upload doesn't work without proper role
        '''
        document = FileStorage(StringIO('test,this,csv'), filename='test.csv').close()
        upload_csv = self.client.post('/conductor/upload_new', data=dict(upload=document))

        self.assertEqual(upload_csv.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.conductor)
        self.assert200(self.client.post('/conductor/upload_new', data=dict(upload=document)))

        self.login_user(self.admin)
        self.assert200(self.client.post('/conductor/upload_new', data=dict(upload=document)))

        self.login_user(self.superadmin)
        self.assert200(self.client.post('/conductor/upload_new', data=dict(upload=document)))

    def test_upload_validation(self):
        '''Test that only csv's can be uploaded
        '''
        csv_document = FileStorage(StringIO('test,this,csv'), filename='test.csv').close()
        txt_document = FileStorage(StringIO('test,this,txt'), filename='test.txt').close()
        self.login_user(self.conductor)

        upload_txt = self.client.post('conductor/upload_new', data=dict(upload=txt_document))
        self.assertTrue(upload_txt.data.count('.csv files only', 1))

        upload_csv = FileUpload('conductor/upload_new', data=dict(upload=csv_document))
        self.assertTrue(upload_csv.data.count('Upload successful', 1))

    @unittest.skip('upload/update test coming soon')
    def test_upload_success(self):
        '''Test that file upload works and updates database
        '''
        self.assertTrue(False)
