# -*- coding: utf-8 -*-

import datetime
from flask import current_app

from purchasing.extensions import db
from purchasing.notifications import Notification
from purchasing.jobs.job_base import JobBase, EmailJobBase

from purchasing.opportunities.models import Opportunity, Vendor, Category
from purchasing.public.models import AppStatus

@JobBase.register
class BeaconNewOppotunityOpenJob(EmailJobBase):
    '''Send a nightly email update when new opportunities are posted
    '''

    def build_notifications(self):
        '''Implements EmailJobBase build_notifications method

        Returns:
            list of :py:class:`~purchasing.notifications.Notification` objects, one
            for each new Opportunity. For each Opportunity, the ``to_email`` field
            is the union of all followers of the opportunity and any followers of
            any categories that the Opportunity has
        '''
        notifications = []
        for opportunity in self.get_opportunities():
            opp_categories = [i.id for i in opportunity.categories]

            category_vendors = Vendor.query.filter(
                Vendor.categories.any(Category.id.in_(opp_categories))
            ).all()

            notifications.append(
                Notification(
                    to_email=set([i.email for i in category_vendors] + [i.email for i in opportunity.vendors]),
                    cc_email=list(),
                    from_email=current_app.config['BEACON_SENDER'],
                    subject='A new City of Pittsburgh opportunity from Beacon!',
                    html_template='opportunities/emails/newopp.html',
                    txt_template='opportunities/emails/newopp.txt',
                    opportunity=opportunity
                )
            )
            opportunity.raw_update(publish_notification_sent=True)

        return notifications

    def get_opportunities(self):
        '''Get new opportunities to send to businesses

        Returns:
            list of :py:class:`~purchasing.opportunities.models.Opportunity` objects
            that are approved (``is_public == True``), have not had notification emails
            sent yet (``publish_notification_sent == False``), and are set to
            publish today (``db.func.DATE(Opportunity.planned_publish) == datetime.date.today()``)
        '''
        return Opportunity.query.filter(
            db.func.DATE(Opportunity.planned_publish) == datetime.date.today(),
            Opportunity.publish_notification_sent == False,
            Opportunity.is_public == True
        ).all()

@JobBase.register
class BeaconBiweeklyDigestJob(EmailJobBase):
    '''Send a biweekly update of all non-expired Opportunities posted to Beacon
    '''
    def run_job(self, job):
        '''Runs the biweekly update job and updates the app status as necessary
        '''
        did_run = super(BeaconBiweeklyDigestJob, self).run_job(job)
        if did_run.status == 'success':
            current_status = AppStatus.query.first()
            current_status.update(last_beacon_newsletter=datetime.datetime.utcnow())

    def should_run(self):
        '''Returns true only if we are on the first or fifteenth of the month or time_override is True
        '''
        return datetime.datetime.today().day in [1, 15] or self.time_override

    def build_notifications(self):
        '''Implements EmailJobBase build_notifications method

        Returns:
            list of :py:class:`~purchasing.notifications.Notification` objects, one
            for each non-expired opportunity that has been published since the last
            Beacon newsletter was sent out
        '''
        notifications = []

        opportunities = self.get_opportunities()

        notifications.append(
            Notification(
                to_email=set([i.email for i in Vendor.newsletter_subscribers()]),
                from_email=current_app.config['BEACON_SENDER'],
                subject='Your biweekly Beacon opportunity summary',
                html_template='opportunities/emails/biweeklydigest.html',
                txt_template='opportunities/emails/biweeklydigest.txt',
                opportunities=opportunities
            )
        )
        return notifications

    def get_opportunities(self):
        '''Get bulk opportunities to send to businesses

        Returns:
            list of :py:class:`~purchasing.opportunities.models.Opportunity` objects
            that have a ``published_at`` date after the last newsletter was sent out
            and expire on or after today
        '''
        current_status = AppStatus.query.first()
        return Opportunity.query.filter(
            Opportunity.published_at > db.func.coalesce(
                current_status.last_beacon_newsletter, datetime.date(2010, 1, 1)
            ), Opportunity.is_public == True,
            Opportunity.planned_submission_end >= datetime.date.today()
        ).all()
