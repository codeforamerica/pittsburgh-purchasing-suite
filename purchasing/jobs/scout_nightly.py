# -*- coding: utf-8 -*-

import datetime

from purchasing.jobs.job_base import EmailJobBase, JobBase
from purchasing.notifications import Notification
from purchasing.tasks import scrape_county_task

from purchasing.data.contracts import ContractBase

@JobBase.register
class CountyScrapeJob(JobBase):
    '''Nightly task to scrape the County for new line item information

    See Also:
        * :py:func:`purchasing.data.importer.scrape_county.main`
        * :py:func:`purchasing.tasks.scrape_county_task`
    '''
    @property
    def start_time(self):
        '''Override default start time, kick scrape task off immediately
        '''
        return None

    def run_job(self, job):
        '''Boot up a scrape county job on a Celery worker (it can be long-running)
        '''
        if job:
            scrape_county_task.delay(job)

class ScoutJobBase(EmailJobBase):
    '''Base class for Scout email notifications

    See Also:
        :py:class:`~purchasing.notifications.Notification`
    '''
    @property
    def notification_props(self):
        '''Placeholder for properties to be assigned to the Notification class.

        Based on the implementation, this dictionary should include at least a
        'subjct' and 'html_template' key.

        Raises:
            NotImplementedError
        '''
        raise NotImplementedError

    def get_expiring_contracts(self):
        '''Get expiring contracts. Must be implemented in subclasses

        Raises:
            NotImplementedError
        '''
        raise NotImplementedError

    def build_notifications(self):
        '''
        '''
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
    '''Get all contracts that expire today and send notification reminders
    '''
    @property
    def notification_props(self):
        return {
            'html_template': '/scout/emails/expired_contract.html',
            'subject': 'A contract that you follow has expired'
        }

    def get_expiring_contracts(self):
        '''Get all contracts expiring today

        Returns:
            List of :py:class:`~purchasing.data.contracts.ContractBase` objects
            that expire today
        '''
        return ContractBase.query.filter(
            ContractBase.expiration_date == datetime.date.today(),
        ).all()

@JobBase.register
class ScoutContractsExpireSoonJob(ScoutJobBase):
    '''Get all contracts that are expiring in 30 days and send reminders
    '''
    @property
    def notification_props(self):
        return {
            'html_template': '/scout/emails/expiring_soon_contract.html',
            'subject': 'A contract that you follow will expire soon'
        }

    def get_expiring_contracts(self):
        '''Get all contracts expiring today

        Returns:
            List of :py:class:`~purchasing.data.contracts.ContractBase` objects
            that expire in 30 days
        '''
        return ContractBase.query.filter(
            ContractBase.expiration_date ==
            datetime.date.today() + datetime.timedelta(days=30),
        ).all()
