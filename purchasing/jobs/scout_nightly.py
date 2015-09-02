# -*- coding: utf-8 -*-

import datetime

from purchasing.jobs.job_base import EmailJobBase, JobBase
from purchasing.notifications import Notification
from purchasing.tasks import scrape_county_task

from purchasing.data.models import ContractBase

@JobBase.register
class CountyScrapeJob(JobBase):
    def run_job(self, job):
        if job:
            scrape_county_task.delay(job)

class ScoutJobBase(EmailJobBase):
    @property
    def notification_props(self):
        raise NotImplementedError

    def build_notifications(self):
        notifications = []
        for contract in self.get_expiring_contracts():
            notifications.append(
                Notification(
                    to_email=[i.email for i in contract.followers],
                    subject=self.notification_props['subject'],
                    html_template=self.notification_props['html_template'],
                    contract=contract
                )
            )
        return notifications

@JobBase.register
class ScoutContractsExpireTodayJob(ScoutJobBase):
    @property
    def notification_props(self):
        return {
            'html_template': '/wexplorer/emails/expired_contract.html',
            'subject': 'A contract that you follow has expired'
        }

    def get_expiring_contracts(self):
        return ContractBase.query.filter(
            ContractBase.expiration_date == datetime.date.today(),
        ).all()

@JobBase.register
class ScoutContractsExpireSoonJob(ScoutJobBase):
    @property
    def notification_props(self):
        return {
            'html_template': '/wexplorer/emails/expiring_soon_contract.html',
            'subject': 'A contract that you follow will expire soon'
        }

    def get_expiring_contracts(self):
        return ContractBase.query.filter(
            ContractBase.expiration_date ==
            datetime.date.today() - datetime.timedelta(days=120),
        ).all()
