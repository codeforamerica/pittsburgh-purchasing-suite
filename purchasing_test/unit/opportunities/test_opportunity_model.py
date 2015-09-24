# -*- coding: utf-8 -*-

import datetime
from unittest import TestCase
from mock import patch

from purchasing_test.factories import OpportunityFactory, UserFactory, RoleFactory, DepartmentFactory

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
