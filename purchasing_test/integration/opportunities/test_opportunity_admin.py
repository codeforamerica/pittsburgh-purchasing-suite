# -*- coding: utf-8 -*-

import datetime

from os import mkdir, listdir, rmdir
from cStringIO import StringIO
from shutil import rmtree

from werkzeug.datastructures import MultiDict
from werkzeug.datastructures import FileStorage

from flask import current_app

from purchasing.database import db
from purchasing.extensions import mail
from purchasing.users.models import User
from purchasing.data.stages import Stage
from purchasing.data.flows import Flow
from purchasing.opportunities.models import Opportunity, Vendor, Category, OpportunityDocument
from purchasing.opportunities.forms import OpportunityDocumentForm
from purchasing.data.importer.nigp import main as import_nigp

from purchasing_test.test_base import BaseTestCase
from purchasing_test.factories import (
    OpportunityDocumentFactory, VendorFactory, DepartmentFactory
)
from purchasing_test.util import (
    insert_a_role, insert_a_user, insert_a_document,
    insert_an_opportunity
)

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

        self.admin = insert_a_user(email='foo@foo.com', role=self.admin_role)
        self.staff = insert_a_user(email='foo2@foo.com', role=self.staff_role)

        self.opportunity1 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today() + datetime.timedelta(1),
            planned_submission_start=datetime.date.today() + datetime.timedelta(2),
            planned_submission_end=datetime.date.today() + datetime.timedelta(2)
        )
        self.opportunity2 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today(),
            planned_submission_start=datetime.date.today() + datetime.timedelta(2),
            planned_submission_end=datetime.date.today() + datetime.timedelta(2),
            categories=set([Category.query.first()])
        )
        self.opportunity3 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today() - datetime.timedelta(2),
            planned_submission_start=datetime.date.today() - datetime.timedelta(2),
            planned_submission_end=datetime.date.today() - datetime.timedelta(1)
        )
        self.opportunity4 = insert_an_opportunity(
            contact=self.admin, created_by=self.staff,
            is_public=True, planned_publish=datetime.date.today() - datetime.timedelta(1),
            planned_submission_start=datetime.date.today(),
            planned_submission_end=datetime.date.today() + datetime.timedelta(2),
            title='TEST TITLE!'
        )

    def tearDown(self):
        super(TestOpportunitiesAdminBase, self).tearDown()
        # clear out the uploads folder
        rmtree(current_app.config.get('UPLOAD_DESTINATION'))
        try:
            rmdir(current_app.config.get('UPLOAD_DESTINATION'))
        except OSError:
            pass

class TestOpportunitiesAdmin(TestOpportunitiesAdminBase):
    render_templates = True

    def test_document_upload(self):
        '''Test document uploads properly
        '''
        # assert that we return none without a document
        form = OpportunityDocumentForm()
        form.document.data = FileStorage(StringIO(''), filename='')
        self.assertEquals((None, None), form.upload_document(1))

        good_form = OpportunityDocumentForm()
        good_form.document.data = FileStorage(StringIO('hello world!'), filename='test.txt')
        good_form.upload_document(1)

        self.assertTrue('opportunity-1-test.txt' in listdir(current_app.config.get('UPLOAD_DESTINATION')))

    def test_build_opportunity_categories(self):
        '''Test categories are added properly
        '''
        self.login_user(self.admin)
        data = {
            'department': str(self.department1.id), 'contact_email': self.admin.email,
            'title': 'NEW_OPPORTUNITY', 'description': 'test',
            'planned_publish': datetime.date.today(),
            'planned_submission_start': datetime.date.today(),
            'planned_submission_end': datetime.date.today() + datetime.timedelta(1),
            'is_public': False, 'subcategories-1': 'on', 'subcategories-2': 'on',
            'subcategories-3': 'on', 'subcategories-4': 'on'
        }

        self.client.post('/beacon/admin/opportunities/new', data=data)

        self.assertEquals(Opportunity.query.count(), 5)
        new_opp = Opportunity.query.filter(Opportunity.title == 'NEW_OPPORTUNITY').first()
        self.assertEquals(len(new_opp.categories), 4)

        new_opp_req = self.client.get('/beacon/opportunities/{}'.format(new_opp.id))
        self.assert200(new_opp_req)

        # because the category is a set, we can't know for sure
        # which tags will be there on page load. however, three should
        # always be there, and one shouldn't be
        match, nomatch, not_associated = 0, 0, 0
        for i in Category.query.all():
            if i.category_friendly_name in new_opp_req.data:
                match += 1
            elif i in self.get_context_variable('opportunity').categories:
                nomatch += 1
            else:
                not_associated += 1

        self.assertEquals(match, 3)
        self.assertEquals(nomatch, 1)
        self.assertEquals(not_associated, 1)

        self.assertTrue('1 more' in new_opp_req.data)

    def test_build_opportunity_new_user(self):
        '''Test that build_opportunity creates new users appropriately
        '''
        self.login_user(self.admin)
        data = {
            'department': str(self.department1.id),
            'contact_email': 'new_email@foo.com',
            'title': 'test', 'description': 'test',
            'planned_publish': datetime.date.today(),
            'planned_submission_start': datetime.date.today(),
            'planned_submission_end': datetime.date.today() + datetime.timedelta(1),
            'is_public': False
        }

        # assert that we create a new user when we build with a new email
        self.assertEquals(User.query.count(), 2)
        self.client.post('/beacon/admin/opportunities/new', data=data)
        self.assertEquals(User.query.count(), 3)

    def test_create_an_opportunity(self):
        '''Test create a new opportunity
        '''
        self.assertEquals(Opportunity.query.count(), 4)
        self.assertEquals(self.client.get('/beacon/admin/opportunities/new').status_code, 302)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')

        self.login_user(self.admin)
        self.assert200(self.client.get('/beacon/admin/opportunities/new'))

        # build data dictionaries
        bad_data = {
            'department': str(self.department1.id), 'contact_email': self.staff.email,
            'title': None, 'description': None,
            'planned_publish': datetime.date.today(),
            'planned_submission_start': datetime.date.today(),
            'planned_submission_end': datetime.date.today() + datetime.timedelta(1),
            'save_type': 'save'
        }

        # assert that you need a title & description
        new_contract = self.client.post('/beacon/admin/opportunities/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert200(new_contract)
        self.assertTrue('This field is required.' in new_contract.data)

        bad_data['title'] = 'Foo'
        bad_data['description'] = 'Bar'
        bad_data['planned_submission_end'] = datetime.date.today() - datetime.timedelta(1)

        # assert you can't create a contract with an expired deadline
        new_contract = self.client.post('/beacon/admin/opportunities/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert200(new_contract)
        self.assertTrue('The deadline has to be after today!' in new_contract.data)

        bad_data['description'] = 'TOO LONG! ' * 500
        new_contract = self.client.post('/beacon/admin/opportunities/new', data=bad_data)
        self.assertEquals(Opportunity.query.count(), 4)
        self.assert200(new_contract)
        self.assertTrue('Text cannot be more than 500 words!' in new_contract.data)

        bad_data['description'] = 'Just right.'
        bad_data['planned_submission_end'] = datetime.date.today() + datetime.timedelta(1)

        new_contract = self.client.post('/beacon/admin/opportunities/new', data=bad_data)
        self.assert_flashes('Opportunity post submitted to OMB!', 'alert-success')

        self.assertEquals(Opportunity.query.count(), 5)

        self.assertFalse(
            Opportunity.query.filter(Opportunity.description == 'Just right.').first().is_public
        )

    def test_edit_an_opportunity(self):
        '''Test updating an opportunity
        '''
        self.assertEquals(len(self.opportunity2.categories), 1)
        self.assertEquals(self.client.get('/beacon/admin/opportunities/{}'.format(
            self.opportunity2.id
        )).status_code, 302)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')

        self.login_user(self.admin)
        self.assert200(self.client.get('/beacon/admin/opportunities/{}'.format(
            self.opportunity2.id
        )))

        self.assert200(self.client.get('/beacon/opportunities'))

        self.assertEquals(len(self.get_context_variable('_open')), 1)
        self.assertEquals(len(self.get_context_variable('upcoming')), 1)

        self.client.post('/beacon/admin/opportunities/{}'.format(self.opportunity2.id), data={
            'planned_submission_start': datetime.date.today(), 'title': 'Updated',
            'is_public': True, 'description': 'Updated Contract!', 'save_type': 'public',
            'contact_email': self.admin.email, 'department': self.department1.id,
            'subcategories-{}'.format(Category.query.all()[-1].id): 'on'
        })

        self.assert200(self.client.get('/beacon/opportunities'))
        self.assertEquals(len(self.opportunity2.categories), 2)
        self.assertEquals(len(self.get_context_variable('_open')), 2)
        self.assertEquals(len(self.get_context_variable('upcoming')), 0)

    def test_delete_document(self):
        '''Test removing documents from opportunities
        '''
        opp = self.opportunity1
        opp.opportunity_documents.append(OpportunityDocumentFactory(
            name='the_test_document', href='test'
        ))
        db.session.commit()

        self.assertEquals(len(opp.opportunity_documents.all()), 1)

        opp_doc = OpportunityDocument.query.filter(OpportunityDocument.name == 'the_test_document').first()
        self.client.get('/beacon/admin/opportunities/{}/document/{}/remove'.format(opp.id, opp_doc.id))
        self.assertEquals(len(opp.opportunity_documents.all()), 1)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')

        self.login_user(self.admin)

        self.client.get('/beacon/admin/opportunities/{}/document/{}/remove'.format(opp.id, '999'))
        self.assertEquals(len(opp.opportunity_documents.all()), 1)
        self.assert_flashes("That document doesn't exist!", 'alert-danger')

        self.client.get('/beacon/admin/opportunities/{}/document/{}/remove'.format(opp.id, opp_doc.id))
        self.assertEquals(len(opp.opportunity_documents.all()), 0)
        self.assert_flashes('Document successfully deleted', 'alert-success')

    def test_contract_detail(self):
        '''Test individual contract opportunity pages
        '''
        self.assert200(self.client.get('/beacon/opportunities/{}'.format(self.opportunity3.id)))
        self.assert200(self.client.get('/beacon/opportunities/{}'.format(self.opportunity4.id)))
        self.assert404(self.client.get('/beacon/opportunities/999'))

    def test_signup_for_multiple_opportunities(self):
        '''Test signup for multiple opportunities
        '''
        self.assertEquals(Vendor.query.count(), 0)
        # duplicates should get filtered out
        post = self.client.post('/beacon/opportunities', data=MultiDict([
            ('email', 'foo@foo.com'), ('business_name', 'foo'),
            ('opportunity', str(self.opportunity3.id)),
            ('opportunity', str(self.opportunity4.id)),
            ('opportunity', str(self.opportunity3.id))
        ]))

        self.assertEquals(Vendor.query.count(), 1)

        # should subscribe that vendor to the opportunity
        self.assertEquals(len(Vendor.query.get(1).opportunities), 2)
        for i in Vendor.query.get(1).opportunities:
            self.assertTrue(i.id in [self.opportunity3.id, self.opportunity4.id])

        # should redirect and flash properly
        self.assertEquals(post.status_code, 302)
        self.assert_flashes('Successfully subscribed for updates!', 'alert-success')

    def test_signup_for_opportunity(self):
        '''Test signup for individual opportunities
        '''
        with mail.record_messages() as outbox:
            self.assertEquals(Vendor.query.count(), 0)
            post = self.client.post('/beacon/opportunities/{}'.format(self.opportunity3.id), data={
                'email': 'foo@foo.com', 'business_name': 'foo'
            })
            # should create a new vendor
            self.assertEquals(Vendor.query.count(), 1)

            # should subscribe that vendor to the opportunity
            self.assertEquals(len(Vendor.query.first().opportunities), 1)
            self.assertTrue(self.opportunity3.id in [i.id for i in Vendor.query.first().opportunities])

            # should redirect and flash properly
            self.assertEquals(post.status_code, 302)
            self.assert_flashes('Successfully subscribed for updates!', 'alert-success')

            self.assertEquals(len(outbox), 1)

    def test_signup_download(self):
        '''Test signup downloads don't work for non-staff
        '''
        request = self.client.get('/beacon/admin/signups')
        self.assertEquals(request.status_code, 302)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')

    def test_signup_download_staff(self):
        '''Test signup downloads work properly
        '''

        # insert some vendors
        self.client.post('/beacon/signup', data={
            'email': 'foo@foo.com', 'business_name': 'foo',
            'subcategories-1': 'on', 'categories': 'Apparel'
        })

        self.client.post('/beacon/signup', data={
            'email': 'foo2@foo.com', 'business_name': 'foo',
            'subcategories-1': 'on', 'subcategories-2': 'on',
            'subcategories-3': 'on', 'subcategories-4': 'on',
            'subcategories-5': 'on', 'categories': 'Apparel'
        })

        self.login_user(self.staff)
        request = self.client.get('/beacon/admin/signups')
        self.assertEquals(request.mimetype, 'text/csv')
        self.assertEquals(
            request.headers.get('Content-Disposition'),
            'attachment; filename=vendors-{}.csv'.format(datetime.date.today())
        )

        # python adds an extra return character to the end,
        # so we chop it off. we should have the header row and
        # the two rows we inserted above
        csv_data = request.data.split('\n')[:-1]

        self.assertEquals(len(csv_data), 3)
        for row in csv_data:
            self.assertEquals(len(row.split(',')), 11)

class TestOpportunitiesPublic(TestOpportunitiesAdminBase):
    def setUp(self):
        super(TestOpportunitiesPublic, self).setUp()
        self.opportunity3.is_public = False
        self.opportunity3.categories = set([Category.query.all()[-1]])
        self.vendor = VendorFactory.create(
            business_name='foobar',
            email='foobar@foo.com',
            categories=set([Category.query.all()[-1]])
        )
        db.session.commit()

        self.opportunity1.created_by = self.staff
        self.opportunity3.created_by = self.staff

    def test_vendor_signup_unpublished(self):
        '''Test vendors can't signup for unpublished opportunities
        '''
        with mail.record_messages() as outbox:
            # vendor should not be able to sign up for unpublished opp
            bad_contract = self.client.post('/beacon/opportunities', data={
                'email': 'foo@foo.com', 'business_name': 'foo',
                'opportunity': str(self.opportunity3.id),
            })
            self.assertEquals(len(Vendor.query.get(1).opportunities), 0)
            self.assertTrue('not a valid choice.' in bad_contract.data)
            self.assertEquals(len(outbox), 0)

    def test_pending_opportunity(self):
        '''Test pending opportunity works as expected for anon user
        '''
        # assert randos can't
        self.opportunity3.is_public = False
        db.session.commit()
        self.assertEquals(self.client.get('/beacon/admin/opportunities/pending').status_code, 302)
        random_publish = self.client.get('/beacon/admin/opportunities/{}/publish'.format(self.opportunity3.id))
        self.assertEquals(random_publish.status_code, 302)
        self.assert_flashes('This feature is for city staff only. If you are staff, log in with your pittsburghpa.gov email using the link to the upper right.', 'alert-warning')
        self.assertFalse(self.opportunity3.is_public)

    def test_pending_opportunity_staff(self):
        '''Test pending opportunity works as expected for staff user
        '''
        # assert staff can get to the page, see the opportunities, but can't publish
        self.login_user(self.staff)
        staff_pending = self.client.get('/beacon/admin/opportunities/pending')
        self.assert200(staff_pending)
        self.assertEquals(len(self.get_context_variable('pending')), 1)
        self.assertTrue('Publish' not in staff_pending.data)
        # make sure staff can't publish somehow
        staff_publish = self.client.get('/beacon/admin/opportunities/{}/publish'.format(self.opportunity3.id))
        self.assert_flashes('You do not have sufficent permissions to do that!', 'alert-danger')
        self.assertEquals(staff_publish.status_code, 302)
        self.assertFalse(self.opportunity3.is_public)

    def test_pending_opportunity_admin(self):
        '''Test pending opportunity works as expected for admin user
        '''
        self.login_user(self.admin)
        admin_pending = self.client.get('/beacon/admin/opportunities/pending')
        self.assert200(admin_pending)
        self.assertEquals(len(self.get_context_variable('pending')), 1)
        self.assertTrue('Publish' in admin_pending.data)
        admin_publish = self.client.get('/beacon/admin/opportunities/{}/publish'.format(
            self.opportunity3.id
        ))
        self.assert_flashes('Opportunity successfully published!', 'alert-success')
        self.assertEquals(admin_publish.status_code, 302)
        self.assertTrue(Opportunity.query.get(self.opportunity3.id).is_public)

    def test_approved_opportunity(self):
        '''Test approved opportunities work as expected for city staff
        '''
        self.login_user(self.admin)
        admin_publish = self.client.get('/beacon/admin/opportunities/{}/publish'.format(
            self.opportunity1.id
        ))
        self.assert_flashes('Opportunity successfully published!', 'alert-success')
        self.assertEquals(admin_publish.status_code, 302)
        self.assertTrue(Opportunity.query.get(self.opportunity1.id).is_public)
        self.assertFalse(Opportunity.query.get(self.opportunity1.id).is_published)
        self.assert200(self.client.get('/beacon/opportunities/{}'.format(self.opportunity1.id)))

        self.logout_user()
        self.assert404(self.client.get('/beacon/opportunities/{}'.format(self.opportunity1.id)))

    def test_pending_notification_email_gated(self):
        '''Test we don't send an email when the opportunity is not published
        '''
        self.login_user(self.admin)
        self.opportunity3.planned_publish = datetime.date.today() + datetime.timedelta(1)
        self.assertFalse(self.opportunity3.publish_notification_sent)
        db.session.commit()

        with mail.record_messages() as outbox:
            self.client.get('/beacon/admin/opportunities/{}/publish'.format(
                self.opportunity3.id
            ))
            self.assertFalse(self.opportunity3.is_published)
            self.assertTrue(self.opportunity3.is_public)
            self.assertFalse(self.opportunity3.publish_notification_sent)
            self.assertEquals(len(outbox), 1)
            self.assertTrue(
                'A new City of Pittsburgh opportunity from Beacon' not in
                [i.subject for i in outbox]
            )

    def test_pending_notification_email(self):
        '''Test we do send an email to vendors when the opportunity is advertised
        '''
        self.login_user(self.admin)
        self.assertFalse(self.opportunity3.publish_notification_sent)

        with mail.record_messages() as outbox:
            self.client.get('/beacon/admin/opportunities/{}/publish'.format(
                self.opportunity3.id
            ))
            self.assertTrue(self.opportunity3.is_published)
            self.assertTrue(self.opportunity3.is_public)
            self.assertTrue(self.opportunity3.publish_notification_sent)
            self.assertEquals(len(outbox), 2)

    def test_create_and_publish_opportunity_as_admin(self):
        '''Test that 'publishing' an opportunity sends the proper emails
        '''
        self.login_user(self.admin)
        self.assertEquals(Opportunity.query.count(), 4)

        with mail.record_messages() as outbox:
            self.client.post('/beacon/admin/opportunities/new', data={
                'department': str(self.department1.id), 'contact_email': self.staff.email,
                'title': 'foo', 'description': 'bar',
                'planned_publish': datetime.date.today(),
                'planned_submission_start': datetime.date.today(),
                'planned_submission_end': datetime.date.today() + datetime.timedelta(1),
                'save_type': 'publish', 'subcategories-{}'.format(Category.query.all()[-1].id): 'on'
            })

            self.assertEquals(Opportunity.query.count(), 5)
            # should send to the single vendor signed up to receive info
            # about that category
            self.assertEquals(len(outbox), 1)
            self.assertEquals(outbox[0].subject, '[Pittsburgh Purchasing] A new City of Pittsburgh opportunity from Beacon!')

    def test_update_and_publish_oppportunity_as_admin(self):
        '''Test that 'publishing' an opportunity sends the proper emails
        '''

        data = {
            'department': str(self.department1.id), 'contact_email': self.staff.email,
            'title': 'test_create_edit_publish', 'description': 'bar',
            'planned_publish': datetime.date.today(),
            'planned_submission_start': datetime.date.today(),
            'planned_submission_end': datetime.date.today() + datetime.timedelta(1),
            'save_type': 'save', 'subcategories-{}'.format(Category.query.all()[-1].id): 'on'
        }

        self.login_user(self.admin)
        self.assertEquals(Opportunity.query.count(), 4)

        with mail.record_messages() as outbox:
            self.client.post('/beacon/admin/opportunities/new', data=data)

            self.assertEquals(Opportunity.query.count(), 5)
            # doesn't send the opportunity yet
            self.assertEquals(len(outbox), 0)

            data.update({'save_type': 'publish'})
            self.client.post('/beacon/admin/opportunities/{}'.format(
                Opportunity.query.filter(Opportunity.title == 'test_create_edit_publish').first().id),
                data=data
            )
            # sends the opportunity when updated with the proper save type
            self.assertEquals(len(outbox), 1)
            self.assertEquals(outbox[0].subject, '[Pittsburgh Purchasing] A new City of Pittsburgh opportunity from Beacon!')
