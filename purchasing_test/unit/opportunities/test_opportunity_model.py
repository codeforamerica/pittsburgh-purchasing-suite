# -*- coding: utf-8 -*-

import datetime
from unittest import TestCase
from mock import patch, Mock

from purchasing.opportunities.models import Opportunity

from purchasing_test.factories import (
    OpportunityFactory, UserFactory, RoleFactory, DepartmentFactory,
    OpportunityDocumentFactory
)

class TestOpportunityModel(TestCase):
    def setUp(self):
        self.yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        self.today = datetime.datetime.today()
        self.tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)

    def test_opportunity_open(self):
        open_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow
        )
        self.assertTrue(open_opportunity.is_published)
        self.assertFalse(open_opportunity.is_upcoming)
        self.assertTrue(open_opportunity.is_submission_start)
        self.assertFalse(open_opportunity.is_submission_end)

    def test_opportunity_open_not_published(self):
        open_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.tomorrow,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow
        )
        self.assertFalse(open_opportunity.is_published)
        self.assertFalse(open_opportunity.is_upcoming)
        self.assertFalse(open_opportunity.is_submission_start)
        self.assertFalse(open_opportunity.is_submission_end)

    def test_opportunity_notpublic(self):
        notpublic_opportunity = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow
        )
        self.assertFalse(notpublic_opportunity.is_published)
        self.assertFalse(notpublic_opportunity.is_upcoming)
        self.assertFalse(notpublic_opportunity.is_submission_start)
        self.assertFalse(notpublic_opportunity.is_submission_end)

    def test_opportunity_pending(self):
        pending_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.tomorrow, planned_submission_end=self.tomorrow
        )
        self.assertTrue(pending_opportunity.is_published)
        self.assertTrue(pending_opportunity.is_upcoming)
        self.assertFalse(pending_opportunity.is_submission_start)
        self.assertFalse(pending_opportunity.is_submission_end)

    def test_opportunity_closed(self):
        closed_opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.yesterday, planned_submission_end=self.yesterday
        )
        self.assertTrue(closed_opportunity.is_published)
        self.assertFalse(closed_opportunity.is_upcoming)
        self.assertFalse(closed_opportunity.is_submission_start)
        self.assertTrue(closed_opportunity.is_submission_end)

        closed_opportunity_today_deadline = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.yesterday, planned_submission_end=self.today
        )
        self.assertTrue(closed_opportunity_today_deadline.is_published)
        self.assertFalse(closed_opportunity_today_deadline.is_upcoming)
        self.assertFalse(closed_opportunity_today_deadline.is_submission_start)
        self.assertTrue(closed_opportunity_today_deadline.is_submission_end)

    def test_can_edit_not_public(self):
        staff = UserFactory.build(role=RoleFactory.build(name='staff'))
        creator = UserFactory.build(role=RoleFactory.build(name='staff'))
        admin = UserFactory.build(role=RoleFactory.build(name='admin'))
        opportunity = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow,
            created_by=creator, contact=creator, created_by_id=creator.id,
            contact_id=creator.id
        )
        self.assertFalse(opportunity.can_edit(staff))
        self.assertTrue(opportunity.can_edit(creator))
        self.assertTrue(opportunity.can_edit(admin))

    def test_can_edit_is_public(self):
        staff = UserFactory.build(role=RoleFactory.build(name='staff'))
        creator = UserFactory.build(role=RoleFactory.build(name='staff'))
        admin = UserFactory.build(role=RoleFactory.build(name='admin'))
        opportunity = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow,
            created_by=creator, created_by_id=creator.id,
            contact_id=creator.id
        )
        self.assertFalse(opportunity.can_edit(staff))
        self.assertFalse(opportunity.can_edit(creator))
        self.assertTrue(opportunity.can_edit(admin))

    def test_has_vendor_documents_needed_true(self):
        opportunity = OpportunityFactory.build(vendor_documents_needed=[1])
        self.assertTrue(opportunity.has_vendor_documents())

    def test_has_vendor_documents_needed_false(self):
        opportunity = OpportunityFactory.build()
        self.assertFalse(opportunity.has_vendor_documents())

        opportunity2 = OpportunityFactory.build(vendor_documents_needed=[])
        self.assertFalse(opportunity.has_vendor_documents())

    def test_vendor_documents_needed_no_docs(self):
        opportunity = OpportunityFactory.build()
        self.assertEquals(opportunity.get_vendor_documents(), [])

    @patch('purchasing.opportunities.models.RequiredBidDocument.query')
    def test_vendor_documents_needed_with_docs(self, query):
        opportunity = OpportunityFactory.build(vendor_documents_needed=[1])
        opportunity.get_vendor_documents()
        self.assertTrue(query.filter.called)

    def test_opportunity_has_docs_true(self):
        opp = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow,
            opportunity_documents=[OpportunityDocumentFactory.build()]
        )
        self.assertTrue(opp.has_docs)

    def test_opportunity_has_docs_false(self):
        opp = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_start=self.today, planned_submission_end=self.tomorrow
        )
        self.assertFalse(opp.has_docs)

    @patch('purchasing.notifications.Notification.send')
    def send_publish_email(self, send):
        should_send = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_end=self.tomorrow,
            publish_notification_sent=False
        )
        self.assertTrue(should_send.send_publish_email())
        self.assertTrue(send.called_once)

        should_not_send = OpportunityFactory.build(
            is_public=True, planned_publish=self.yesterday,
            planned_submission_end=self.tomorrow,
            publish_notification_sent=True
        )
        self.assertFalse(should_not_send.send_publish_email())
        self.assertTrue(send.called_once)

        should_not_send2 = OpportunityFactory.build(
            is_public=False, planned_publish=self.yesterday,
            planned_submission_end=self.tomorrow,
            publish_notification_sent=False
        )
        self.assertFalse(should_not_send2.send_publish_email())
        self.assertTrue(send.called_once)
