# -*- coding: utf-8 -*-

import datetime

from purchasing.extensions import mail

from purchasing.jobs.scout_nightly import (
    ScoutContractsExpireSoonJob, ScoutContractsExpireTodayJob
)

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.factories import ContractBaseFactory, UserFactory

class TestScoutJobs(BaseTestCase):
    def setUp(self):
        super(TestScoutJobs, self).setUp()
        self.user = UserFactory.create()
        ContractBaseFactory.create(
            expiration_date=datetime.date.today() + datetime.timedelta(120),
            description='foobar',
            followers=[self.user]
        )

        ContractBaseFactory.create(
            expiration_date=datetime.date.today(),
            description='qux',
            followers=[self.user]
        )

        ContractBaseFactory.create(
            expiration_date=datetime.date.today() + datetime.timedelta(1),
            description='qux',
            followers=[self.user]
        )

    def test_scout_expiration_nightly(self):
        nightly = ScoutContractsExpireTodayJob(time_override=True)
        scheduled, existing_job = nightly.schedule_job()
        with mail.record_messages() as outbox:
            nightly.run_job(scheduled)
            self.assertEquals(len(outbox), 1)
            self.assertEquals(
                outbox[0].subject,
                '[Pittsburgh Purchasing] ' + nightly.notification_props['subject']
            )

    def test_scout_expiration_soon(self):
        nightly = ScoutContractsExpireSoonJob(time_override=True)
        scheduled, existing_job = nightly.schedule_job()
        with mail.record_messages() as outbox:
            nightly.run_job(scheduled)
            self.assertEquals(len(outbox), 1)
            self.assertEquals(
                outbox[0].subject,
                '[Pittsburgh Purchasing] ' + nightly.notification_props['subject']
            )
