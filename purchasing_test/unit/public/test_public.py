# -*- coding: utf-8 -*-

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_user, insert_a_role
)

class TestPublic(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestPublic, self).setUp()
        # create a conductor and general staff person
        self.conductor_role_id = insert_a_role('conductor')
        self.staff_role_id = insert_a_role('staff')
        self.conductor = insert_a_user(role=self.conductor_role_id)
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role_id)

    def test_public(self):
        '''Make sure that all of the public pages work as expected
        '''
        public_viewer = self.client.get('/')
        self.assert200(public_viewer)
        self.assertTrue('<i class="fa fa-train fa-stack-1x fa-body-bg"></i>' not in public_viewer.data)

        self.login_user(self.staff)
        staff_view = self.client.get('/')
        self.assert200(staff_view)
        self.assertTrue('<i class="fa fa-train fa-stack-1x fa-body-bg"></i>' not in staff_view.data)

        self.login_user(self.conductor)
        conductor_view = self.client.get('/')
        self.assert200(conductor_view)
        self.assertTrue('<i class="fa fa-train fa-stack-1x fa-body-bg"></i>' in conductor_view.data)

        self.login_user(self.conductor)
        admin_view = self.client.get('/')
        self.assert200(admin_view)
        self.assertTrue('<i class="fa fa-train fa-stack-1x fa-body-bg"></i>' in admin_view.data)
