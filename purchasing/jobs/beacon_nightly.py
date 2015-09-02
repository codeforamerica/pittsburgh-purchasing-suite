# -*- coding: utf-8 -*-

from purchasing.jobs.job_base import EmailJobBase
from purchasing.notifications import Notification

class BeaconNewOppotunityOpen(EmailJobBase):
    def build_notification(self):
        pass

    def get_recipients(self):
        pass
