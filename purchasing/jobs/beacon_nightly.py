# -*- coding: utf-8 -*-

import datetime

from purchasing.extensions import db
from purchasing.notifications import Notification
from purchasing.jobs.job_base import JobBase, EmailJobBase

from purchasing.opportunities.models import Opportunity, Vendor, Category
from purchasing.public.models import AppStatus

@JobBase.register
class BeaconNewOppotunityOpenJob(EmailJobBase):
    def build_notifications(self):
        notifications = []
        for opportunity in self.get_opportunities():
            opp_categories = [i.id for i in opportunity.categories]

            category_vendors = Vendor.query.filter(
                Vendor.categories.any(Category.id.in_(opp_categories))
            ).all()

            notifications.append(
                Notification(
                    to_email=set([i.email for i in category_vendors] + [i.email for i in opportunity.vendors]),
                    subject='A new City of Pittsburgh opportunity from Beacon!',
                    html_template='opportunities/emails/newopp.html',
                    txt_template='opportunities/emails/newopp.txt',
                    opportunity=opportunity
                )
            )
            opportunity.update(publish_notification_sent=True)

        return notifications

    def get_opportunities(self):
        return Opportunity.query.filter(
            db.func.DATE(Opportunity.planned_publish) == datetime.date.today(),
            Opportunity.publish_notification_sent == False,
            Opportunity.is_public == True
        ).all()

class BeaconBiweeklyDigestJob(EmailJobBase):
    def run_job(self, job):
        did_run = super(BeaconBiweeklyDigestJob, self).run_job(job)
        if did_run is not None:
            current_status = AppStatus.query.first()
            current_status.update(last_beacon_newsletter=datetime.datetime.utcnow())

    def should_run(self):
        return datetime.datetime.today().day in [1, 15] or self.time_override

    def build_notifications(self):
        notifications = []

        opportunities = self.get_opportunities()
        notifications.append(
            Notification(
                to_email=set([i.email for i in Vendor.newsletter_subscribers()]),
                subject='Your biweekly Beacon opportunity summary',
                html_template='opportunities/emails/biweeklydigest.html',
                txt_template='opportunities/emails/biweeklydigest.txt',
                opportunities=opportunities
            )
        )
        return notifications

    def get_opportunities(self):
        current_status = AppStatus.query.first()
        return Opportunity.query.filter(
            Opportunity.published_at > db.func.coalesce(
                current_status.last_beacon_newsletter, datetime.date(2010, 1, 1)
            ), Opportunity.is_published == True
        ).all()
