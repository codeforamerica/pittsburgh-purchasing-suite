# -*- coding: utf-8 -*-

import datetime

from purchasing.extensions import mail

from purchasing.jobs.beacon_nightly import (
    BeaconNewOppotunityOpenJob,
)

from purchasing_test.test_base import BaseTestCase
from purchasing_test.factories import OpportunityFactory, VendorFactory, CategoryFactory

class TestBeaconJobs(BaseTestCase):
    def setUp(self):
        super(TestBeaconJobs, self).setUp()

        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        today = datetime.datetime.today()
        tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)

        self.category = CategoryFactory.create()

        self.opportunity = OpportunityFactory.create(
            is_public=True, planned_publish=today, planned_submission_start=today,
            planned_submission_end=tomorrow, categories=set([self.category])
        )
        self.opportunity2 = OpportunityFactory.create(
            is_public=True, planned_publish=yesterday, planned_submission_start=today,
            planned_submission_end=tomorrow, publish_notification_sent=True,
            categories=set([self.category])
        )
        self.opportunity3 = OpportunityFactory.create(
            is_public=False, planned_publish=today, planned_submission_start=today,
            planned_submission_end=tomorrow, publish_notification_sent=False,
            categories=set([self.category])
        )

        VendorFactory.create(opportunities=set([self.opportunity]))
        VendorFactory.create(categories=set([self.category]))

    def test_beacon_new_opportunity_nightly(self):
        nightly = BeaconNewOppotunityOpenJob(time_override=True)
        scheduled, existing_job = nightly.schedule_job()

        with mail.record_messages() as outbox:
            nightly.run_job(scheduled)
            self.assertEquals(len(outbox), 2)
            self.assertEquals(
                outbox[0].subject,
                '[Pittsburgh Purchasing] A new City of Pittsburgh opportunity from Beacon!'
            )
            self.assertTrue(self.opportunity.publish_notification_sent)

    def test_correct_opportunities_queried(self):
        nightly = BeaconNewOppotunityOpenJob()

        opportunities = nightly.get_opportunities()
        self.assertEquals(len(opportunities), 1)
        self.assertTrue(self.opportunity in opportunities)
        self.assertFalse(self.opportunity2 in opportunities)
        self.assertFalse(self.opportunity3 in opportunities)
