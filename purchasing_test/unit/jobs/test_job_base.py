# -*- coding: utf-8 -*-

import datetime
import pytz

from unittest import TestCase
from mock import patch, Mock, call

from purchasing.jobs.job_base import JobBase, EmailJobBase

from purchasing_test.factories import JobStatusFactory

import logging
logging.getLogger("factory").setLevel(logging.WARN)

class FakeJobBase(JobBase):
    jobs = []

    @property
    def start_time(self):
        return None

    @property
    def job_status_model(self):
        return JobStatusFactory

@FakeJobBase.register
class FakeJob(FakeJobBase):
    pass

class PastJob(FakeJobBase):
    @property
    def start_time(self):
        return (datetime.datetime.utcnow() - datetime.timedelta(minutes=1)).replace(tzinfo=pytz.UTC)

class FutureJob(FakeJobBase):
    @property
    def start_time(self):
        return (datetime.datetime.utcnow() + datetime.timedelta(minutes=1)).replace(tzinfo=pytz.UTC)

class FakeEmailJob(EmailJobBase):
    @property
    def job_status_model(self):
        return JobStatusFactory

class TestJobBase(TestCase):
    def test_register_job(self):
        self.assertEquals(len(FakeJobBase.jobs), 1)
        self.assertTrue(FakeJob in FakeJobBase.jobs)

    @patch('purchasing.jobs.job_base.get_or_create', return_value=[JobStatusFactory.build(), True])
    def test_schedule_timer_no_time(self, get_or_create):
        FakeJob().schedule_job()
        self.assertTrue(get_or_create.called)

    @patch('purchasing.jobs.job_base.get_or_create', return_value=[JobStatusFactory.build(), True])
    def test_schedule_timer_past_job(self, get_or_create):
        PastJob().schedule_job()
        self.assertTrue(get_or_create.called)

    @patch('purchasing.jobs.job_base.get_or_create', return_value=[JobStatusFactory.build(), True])
    def test_schedule_timer_future_job(self, get_or_create):
        FutureJob().schedule_job()
        self.assertFalse(get_or_create.called)

class TestEmailJobBase(TestCase):
    def setUp(self):
        job_mock = Mock()
        job_mock.update = Mock()
        self.job = job_mock

        notification_mock = Mock()
        notification_mock.send = Mock()

        notification_fail = Mock()
        notification_fail.send = Mock(side_effect=Exception('something went wrong!'))

        self.success_notification = notification_mock
        self.failure_notification = notification_fail

    def tearDown(self):
        self.job.reset_mock()

    def test_all_successful(self):
        send_mock = Mock()
        send_mock.return_value = [self.success_notification, self.success_notification]
        FakeEmailJob.build_notifications = send_mock

        expected_updates = [call.update(status='started'), call.update(status='success')]

        FakeEmailJob().run_job(self.job)

        self.assertEquals(self.job.mock_calls, expected_updates)

    def test_some_failures(self):
        send_mock = Mock()
        send_mock.return_value = [self.success_notification, self.failure_notification]
        FakeEmailJob.build_notifications = send_mock

        expected_updates = [
            call.update(status='started'),
            call.update(status='failed', info='something went wrong!')
        ]

        FakeEmailJob().run_job(self.job)

        self.assertEquals(self.job.mock_calls, expected_updates)
