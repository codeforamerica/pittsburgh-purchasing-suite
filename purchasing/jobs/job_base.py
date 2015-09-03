# -*- coding: utf-8 -*-

import datetime
from purchasing.database import Model, db, get_or_create

class JobStatus(Model):
    __tablename__ = 'job_status'

    name = db.Column(db.String(255), primary_key=True)
    date = db.Column(db.DateTime, primary_key=True)
    status = db.Column(db.String, default='new')
    info = db.Column(db.Text)

class JobBase(object):
    def __init__(self):
        self.name = self.__class__.__name__

    jobs = []

    @classmethod
    def register(cls, subcl):
        cls.jobs.append(subcl)
        return subcl

    @property
    def start_time(self):
        return None

    @property
    def job_status_model(self):
        return JobStatus

    def schedule_job(self):
        if self.start_time is None or datetime.datetime.now().time() > self.start_time:
            return get_or_create(
                db.session, self.job_status_model, create_method='create',
                name=self.name, date=datetime.date.today(), status='new'
            )

    def run_job(self, job):
        raise NotImplementedError

class EmailJobBase(JobBase):
    def run_job(self, job):
        if job:
            success = True
            job.update(status='started')
            notifications = self.build_notifications()
            for notification in notifications:
                try:
                    notification.send(multi=True)
                except Exception, e:
                    job.update(status='failed', info=str(e))
                    success = False
            if success:
                job.update(status='success')

        return job

    def build_notifications(self):
        raise NotImplementedError
