# -*- coding: utf-8 -*-

import datetime
from purchasing.database import Model, db, get_or_create

import pytz

EASTERN = pytz.timezone('US/Eastern')
UTC = pytz.UTC

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
        '''Must return a timezone aware datetime.time or datetime.datetime object.

        Datetime.datetime objects are better to return because time objects must
        have dates attached to them to do accurate time comparison around the date
        changeovers.
        '''
        return datetime.datetime.today().replace(
            hour=7, minute=0, second=0, tzinfo=EASTERN
        )

    @property
    def job_status_model(self):
        return JobStatus

    def build_datetime_object(self, time):
        '''Take a datetime.time object and return today's date with the passed
        time's arguments replacing the today time.
        '''
        tzinfo = time.tzinfo if time.tzinfo else UTC

        return datetime.datetime.today().replace(
            hour=time.hour, minute=time.minute, second=time.second, tzinfo=tzinfo
        )

    def schedule_job(self):
        '''Schedule a job.
        '''
        start_time = self.start_time

        if isinstance(self.start_time, datetime.time):
            start_time = self.build_datetime_object(self.start_time)

        if start_time is None or UTC.localize(datetime.datetime.utcnow()) > start_time.astimezone(UTC):
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
