# -*- coding: utf-8 -*-

from os import mkdir, listdir, rmdir
import datetime
from flask import current_app
from werkzeug.datastructures import MultiDict
from cStringIO import StringIO
from werkzeug.datastructures import FileStorage
from shutil import rmtree

from purchasing.opportunities.models import Opportunity, Vendor, Category
from purchasing.users.models import User
from purchasing.data.importer.nigp import main as import_nigp
from purchasing.opportunities.views.admin import build_opportunity, upload_document

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_role, insert_a_user, insert_a_document,
    insert_an_opportunity
)

class TestOpportunities(BaseTestCase):
    render_templates = True

    def setUp(self):
        super(TestOpportunities, self).setUp()

        try:
            mkdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            rmtree(current_app.config.get('UPLOAD_DESTINATION'))
            mkdir(current_app.config.get('UPLOAD_DESTINATION'))

        import_nigp(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/nigp.csv')

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
        self.opportunity4 = insert_an_opportunity(
            contact_id=self.admin.id, created_by=self.staff.id, required_documents=[self.document],
            is_public=False, planned_open=datetime.date.today() + datetime.timedelta(1),
            planned_deadline=datetime.date.today() + datetime.timedelta(2), title='TEST TITLE!'
        )

    def tearDown(self):
        super(TestOpportunities, self).tearDown()
        # clear out the uploads folder
        rmtree(current_app.config.get('UPLOAD_DESTINATION'))
        try:
            rmdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            pass

    def test_document_upload(self):
        '''Test document uploads properly
        '''
        # assert that we return none without a document
        no_document = FileStorage(StringIO(''), filename='')
        self.assertEquals((None, None), upload_document(no_document))

        document = FileStorage(StringIO('hello world!'), filename='test.txt')
        upload_document(document)

        self.assertTrue('test.txt' in listdir(current_app.config.get('UPLOAD_DESTINATION')))

    def test_build_opportunity_categories(self):
        '''Test categories are added properly
        '''
        self.login_user(self.admin)
        data = {
            'department': 'Other', 'contact_email': self.admin.email,
            'title': 'test', 'description': 'test', 'planned_open': datetime.date.today(),
            'planned_deadline': datetime.date.today() + datetime.timedelta(1),
            'is_public': False, 'subcategories-1': 'on', 'subcategories-2': 'on',
            'subcategories-3': 'on', 'subcategories-4': 'on'
        }

        self.client.post('/beacon/opportunities/admin/new', data=data)

        self.assertEquals(Opportunity.query.count(), 5)
        self.assertEquals(len(Opportunity.query.get(5).categories), 4)

        new_opp = self.client.get('/beacon/opportunities/5')
        self.assert200(new_opp)

        # because the category is a set, we can't know for sure
        # which tags will be there on page load. however, three should
        # always be there, and one shouldn't be
        match, nomatch, not_associated = 0, 0, 0
        for i in Category.query.all():
            if i.category_friendly_name in new_opp.data:
                match += 1
            elif i in self.get_context_variable('opportunity').categories:
                nomatch += 1
            else:
                not_associated += 1

        self.assertEquals(match, 3)
        self.assertEquals(nomatch, 1)
        self.assertEquals(not_associated, 1)

        self.assertTrue('1 more' in new_opp.data)

    def test_build_opportunity_new_user(self):
        '''Test that build_opportunity creates new users appropriately
        '''
        data = {
            'department': 'Other', 'contact_email': 'new_email@foo.com',
            'title': 'test', 'description': 'test', 'planned_open': datetime.date.today(),
            'planned_deadline': datetime.date.today() + datetime.timedelta(1),
            'is_public': False
        }

        # assert that we create a new user when we build with a new email
        self.assertEquals(User.query.count(), 2)
        build_opportunity(data, None)
        self.assertEquals(User.query.count(), 3)

    def test_create_a_contract(self):
        '''Test create contract page
        '''
        self.assertEquals(Opportunity.query.count(), 4)
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
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert200(new_contract)
        self.assertTrue('This field is required.' in new_contract.data)

        bad_data['title'] = 'Foo'
        bad_data['description'] = 'Bar'
        bad_data['planned_deadline'] = datetime.date.today() - datetime.timedelta(1)

        # assert you can't create a contract with an expired deadline
        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert200(new_contract)
        self.assertTrue('The deadline has to be after today!' in new_contract.data)

        bad_data['description'] = 'TOO LONG! ' * 500
        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert200(new_contract)
        self.assertTrue('Text cannot be more than 500 words!' in new_contract.data)

        bad_data['description'] = 'Just right.'
        bad_data['is_public'] = True
        bad_data['planned_deadline'] = datetime.date.today() + datetime.timedelta(1)

        new_contract = self.client.post('/beacon/opportunities/admin/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 5)
        self.assert_flashes('Opportunity Successfully Created!', 'alert-success')

    def test_edit_a_contract(self):
        '''Test updating a contract
        '''
        self.assertEquals(self.client.get('/beacon/opportunities/2/admin/edit').status_code, 302)
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')

        self.login_user(self.admin)
        self.assert200(self.client.get('/beacon/opportunities/2/admin/edit'))

        self.assert200(self.client.get('/beacon/opportunities'))

        self.assertEquals(len(self.get_context_variable('active')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 2)

        self.client.post('/beacon/opportunities/2/admin/edit', data={
            'planned_open': datetime.date.today(), 'title': 'Updated',
            'description': 'Updated Contract!', 'is_public': True
        })
        self.assert_flashes('Opportunity Successfully Updated!', 'alert-success')

        self.assert200(self.client.get('/beacon/opportunities'))
        self.assertEquals(len(self.get_context_variable('active')), 2)
        self.assertEquals(len(self.get_context_variable('upcoming')), 1)

    def test_browse_contract(self):
        '''Test browse page loads properly
        '''
        # test admin view restrictions
        self.logout_user()
        no_user = self.client.get('/beacon/opportunities')
        self.assert200(no_user)
        self.assertEquals(len(self.get_context_variable('active')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 2)
        self.assertTrue('TEST TITLE!' not in no_user.data)

        self.login_user(self.admin)
        good_user = self.client.get('/beacon/opportunities')
        self.assert200(good_user)
        self.assertEquals(len(self.get_context_variable('active')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 2)
        self.assertTrue('TEST TITLE!' in good_user.data)
        self.assertEquals(Opportunity.query.count(), 4)

    def test_contract_detail(self):
        '''Test individual contract opportunity pages
        '''
        self.assert200(self.client.get('/beacon/opportunities/1'))
        self.assert200(self.client.get('/beacon/opportunities/2'))
        self.assert404(self.client.get('/beacon/opportunities/999'))

    def test_signup_for_multiple_opportunities(self):
        '''Test signup for multiple opportunities
        '''
        self.assertEquals(Vendor.query.count(), 0)
        # duplicates should get filtered out
        post = self.client.post('/beacon/opportunities', data=MultiDict([
            ('email', 'foo@foo.com'), ('business_name', 'foo'),
            ('opportunity', '1'), ('opportunity', '2'), ('opportunity', '1')
        ]))

        self.assertEquals(Vendor.query.count(), 1)

        # should subscribe that vendor to the opportunity
        self.assertEquals(len(Vendor.query.get(1).opportunities), 2)
        for i in Vendor.query.get(1).opportunities:
            self.assertTrue(i.id in [1, 2])

        # should redirect and flash properly
        self.assertEquals(post.status_code, 302)
        self.assert_flashes('Successfully subscribed for updates!', 'alert-success')

        # vendor should not be able to sign up for unpublished opp
        self.client.post('/beacon/opportunities', data={
            'email': 'foo@foo.com', 'business_name': 'foo',
            'opportunity': '3', 'opportunity': '4'
        })
        self.assertEquals(len(Vendor.query.get(1).opportunities), 2)
        self.assert_flashes('You can\'t subscribe to that contract!', 'alert-danger')

    def test_signup_for_opportunity(self):
        '''Test signup for individual opportunities
        '''
        self.assertEquals(Vendor.query.count(), 0)
        post = self.client.post('/beacon/opportunities/1', data={
            'email': 'foo@foo.com', 'business_name': 'foo'
        })
        # should create a new vendor
        self.assertEquals(Vendor.query.count(), 1)

        # should subscribe that vendor to the opportunity
        self.assertEquals(len(Vendor.query.get(1).opportunities), 1)
        self.assertTrue(1 in [i.id for i in Vendor.query.get(1).opportunities])

        # should redirect and flash properly
        self.assertEquals(post.status_code, 302)
        self.assert_flashes('Successfully subscribed for updates!', 'alert-success')
