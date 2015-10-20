# -*- coding: utf-8 -*-

import datetime

from os import mkdir, rmdir
from shutil import rmtree

from flask import current_app

from purchasing.opportunities.models import Category, Vendor
from purchasing.data.importer.nigp import main as import_nigp

from purchasing_test.test_base import BaseTestCase
from purchasing_test.factories import DepartmentFactory, ContractTypeFactory

from purchasing_test.util import (
    insert_a_role, insert_a_user, insert_a_document,
    insert_an_opportunity
)

class TestOpportunitiesFrontBase(BaseTestCase):
    def setUp(self):
        super(TestOpportunitiesFrontBase, self).setUp()
        import_nigp(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

class TestOpportunitiesAdminBase(BaseTestCase):
    def setUp(self):
        super(TestOpportunitiesAdminBase, self).setUp()
        try:
            mkdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            rmtree(current_app.config.get('UPLOAD_DESTINATION'))
            mkdir(current_app.config.get('UPLOAD_DESTINATION'))

        import_nigp(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

        self.admin_role = insert_a_role('admin')
        self.staff_role = insert_a_role('staff')
        self.department1 = DepartmentFactory(name='test')
        self.opportunity_type = ContractTypeFactory.create(allow_opportunities=True)

        self.admin = insert_a_user(email='foo@foo.com', role=self.admin_role)
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role)

        self.document = insert_a_document()

        self.vendor = Vendor.create(email='foo@foo.com', business_name='foo2')

        self.opportunity1 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            title='tést unïcode title', description='tést unïcode déscription',
            is_public=True, planned_publish=datetime.date.today() + datetime.timedelta(1),
            planned_submission_start=datetime.date.today() + datetime.timedelta(2),
            planned_submission_end=datetime.datetime.today() + datetime.timedelta(2),
            documents=[self.document.id], categories=set([Category.query.first()])
        )
        self.opportunity2 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today(),
            planned_submission_start=datetime.date.today() + datetime.timedelta(2),
            planned_submission_end=datetime.datetime.today() + datetime.timedelta(2),
            categories=set([Category.query.first()])
        )
        self.opportunity3 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today() - datetime.timedelta(2),
            planned_submission_start=datetime.date.today() - datetime.timedelta(2),
            planned_submission_end=datetime.datetime.today() - datetime.timedelta(1),
            categories=set([Category.query.first()])
        )
        self.opportunity4 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today() - datetime.timedelta(1),
            planned_submission_start=datetime.date.today(),
            planned_submission_end=datetime.datetime.today() + datetime.timedelta(2),
            title='TEST TITLE!', categories=set([Category.query.first()])
        )

    def tearDown(self):
        super(TestOpportunitiesAdminBase, self).tearDown()
        # clear out the uploads folder
        rmtree(current_app.config.get('UPLOAD_DESTINATION'))
        try:
            rmdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            pass
