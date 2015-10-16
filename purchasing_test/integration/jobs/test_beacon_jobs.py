# -*- coding: utf-8 -*-

import datetime

from mock import patch, Mock

from purchasing.extensions import mail

from purchasing.public.models import AppStatus
from purchasing.jobs.beacon_nightly import BeaconNewOppotunityOpenJob, BeaconBiweeklyDigestJob
from purchasing.jobs.job_base import JobStatus

from purchasing_test.test_base import BaseTestCase
from purchasing_test.factories import OpportunityFactory, VendorFactory, CategoryFactory, UserFactory

class TestBeaconJobs(BaseTestCase):
    def setUp(self):
        super(TestBeaconJobs, self).setUp()

        self.yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        today = datetime.datetime.today()
        tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)

        self.category = CategoryFactory.create()
        self.admin = UserFactory.create()

        self.opportunity = OpportunityFactory.create(
            is_public=True, planned_publish=today, planned_submission_start=today,
            planned_submission_end=tomorrow, categories=set([self.category]),
            created_by=self.admin, published_at=today
        )
        self.opportunity2 = OpportunityFactory.create(
            is_public=True, planned_publish=self.yesterday, planned_submission_start=today,
            planned_submission_end=tomorrow, publish_notification_sent=True,
            categories=set([self.category]), created_by=self.admin, published_at=self.yesterday
        )
        self.opportunity3 = OpportunityFactory.create(
            is_public=False, planned_publish=today, planned_submission_start=today,
            planned_submission_end=tomorrow, publish_notification_sent=False,
            categories=set([self.category]), created_by=self.admin, published_at=today
        )
        self.opportunity4 = OpportunityFactory.create(
            is_public=True, planned_publish=self.yesterday, planned_submission_start=self.yesterday,
            planned_submission_end=today, publish_notification_sent=True,
            categories=set([self.category]), created_by=self.admin, published_at=self.yesterday
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

    def test_correct_nightly_opportunities_queried(self):
        nightly = BeaconNewOppotunityOpenJob(time_override=True)
        opportunities = nightly.get_opportunities()
        self.assertEquals(len(opportunities), 1)
        self.assertTrue(self.opportunity in opportunities)
        self.assertFalse(self.opportunity2 in opportunities)
        self.assertFalse(self.opportunity3 in opportunities)

    def test_beacon_biweekly_correct_opportunities(self):
        AppStatus.create(last_beacon_newsletter=self.yesterday)
        biweekly = BeaconBiweeklyDigestJob()
        opportunities = biweekly.get_opportunities()
        self.assertEquals(len(opportunities), 1)

    @patch('purchasing.jobs.job_base.EmailJobBase.run_job', side_effect=[JobStatus(status='skipped'), JobStatus(status='success')])
    @patch('purchasing.jobs.beacon_nightly.AppStatus')
    def test_beacon_nightly_update(self, status, run_job):
        status.query.first.return_value = AppStatus()
        AppStatus.update = Mock()

        biweekly = BeaconBiweeklyDigestJob()
        biweekly.run_job(JobStatus(status='new'))
        self.assertFalse(AppStatus.update.called)

        biweekly.run_job(JobStatus(status='new'))
        self.assertTrue(AppStatus.update.called)
