# -*- coding: utf-8 -*-

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_role, insert_a_user
)

class TestCostarsUpload(BaseTestCase):
    def setUp(self):
        super(TestCostarsUpload, self).setUp()

        self.conductor_role_id = insert_a_role('conductor')
        self.conductor = insert_a_user(role=self.conductor_role_id)

        self.staff_role_id = insert_a_role('staff')
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role_id)

        self.login_user(self.conductor)

    def test_page_locked(self):
        '''Test page won't render for people without proper roles
        '''
        # test that you can't access upload page unless you are signed in with proper role
        request = self.client.get('/conductor/upload_new')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.conductor)
        self.client.get('/conductor/upload_new')

        self.login_user(self.admin_user)
        self.client.get('/conductor/upload_new')

        self.login_user(self.superadmin_user)
        self.client.get('/conductor/upload_new')

    def test_upload_locked(self):
        '''Test upload doesn't work without proper role
        '''
        request = self.client.post('/conductor/_process_file')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.conductor)
        self.client.post('/conductor/_process_file')

        self.login_user(self.admin_user)
        self.client.post('/conductor/_process_file')

        self.login_user(self.superadmin_user)
        self.client.post('/conductor/_process_file')

    def test_upload_validation(self):
        '''Test that only csv's can be uploaded
        '''
        self.assertTrue(False)

    def test_upload_success(self):
        '''Test that file upload works and updates database
        '''
        self.assertTrue(False)
