# -*- coding: utf-8 -*-

import datetime

from purchasing.extensions import db
from purchasing.notifications import Notification
from purchasing.jobs.job_base import JobBase, EmailJobBase

from purchasing.opportunities.models import Opportunity, Vendor, Category

@JobBase.register
class BeaconNewOppotunityOpenJob(EmailJobBase):
    def build_notifications(self):
        notifications = []
        for opportunity in self.get_opportunities():
            opp_categories = [i.id for i in opportunity.categories]

            category_vendors = Vendor.query.filter(
                Vendor.categories.any(Category.id.in_(opp_categories))
            ).all()

            import pdb; pdb.set_trace()

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
    def build_notifications(self):
        pass

    def get_recipients(self):
        pass
