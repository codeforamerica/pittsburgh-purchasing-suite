# -*- coding: utf-8 -*-

from purchasing.notifications import Notification
from purchasing.jobs.job_base import JobBase, EmailJobBase

from purchasing.opportunities.models import Opportunity, Vendor, Category

@JobBase.register
class BeaconNewOppotunityOpenJob(EmailJobBase):
    def build_notifications(self):
        notifications = []
        for opportunity in self.get_opportunities():
            opp_categories = [i.id for i in opportunity.categories]

            vendors = Vendor.query.filter(
                Vendor.categories.any(Category.id.in_(opp_categories))
            ).all()

            notifications.append(
                Notification(
                    to_email=[i.email for i in vendors],
                    subject='A new City of Pittsburgh opportunity from Beacon!',
                    html_template='opportunities/emails/newopp.html',
                    txt_template='opportunities/emails/newopp.txt',
                    opportunity=opportunity
                )
            )

        return notifications

    def get_recipients(self):
        pass

@JobBase.register
class BeaconBiweeklyDigestJob(EmailJobBase):
    def build_notifications(self):
        pass

    def get_recipients(self):
        pass
