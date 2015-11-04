# -*- coding: utf-8 -*-

import datetime
from purchasing.database import Model, db, get_or_create

import pytz

EASTERN = pytz.timezone('US/Eastern')
UTC = pytz.UTC

class JobStatus(Model):
    '''Model to track nightly job status and reporting

    JobStatus has a primary compound key of name + date

    Args:
        name: Name of the job
        date: Date the job is scheduled for
        status: String of the job status, defaults to 'new',
            set to 'started', 'success', 'failure', or 'skipped'
        info: Any additional reporting about the job status,
            such as an error message if the job fails
    '''
    __tablename__ = 'job_status'

    name = db.Column(db.String(255), primary_key=True)
    date = db.Column(db.DateTime, primary_key=True)
    status = db.Column(db.String, default='new')
    info = db.Column(db.Text)

class JobBase(object):
    '''Base model for nightly jobs

    Attributes
        jobs:

    Arguments
        name:
        time_override:
    '''
    def __init__(self, time_override=False):
        self.name = self.__class__.__name__
        self.time_override = time_override

    jobs = []

    @classmethod
    def register(cls, subcl):
        '''decorator to allow for explicit job registration

        Example
            Register ``MySubJob`` as a valid job on JobBase

            .. code-block:: python

                @JobBase.register
                class MySubJob(JobBase):
                    def run_job(self, job):
                        pass

        '''
        cls.jobs.append(subcl)
        return subcl

    @property
    def start_time(self):
        '''The time when the job will be scheduled

        Datetime.datetime objects are better to return because time objects must
        have dates attached to them to do accurate time comparison around the date
        changeovers.

        Returns:
            datetime.datetime or datetime.date object, defaults to 7AM EST
        '''
        return datetime.datetime.today().replace(
            hour=7, minute=0, second=0, tzinfo=EASTERN
        )

    @property
    def job_status_model(self):
        '''
        '''
        return JobStatus

    def build_datetime_object(self, time):
        '''Take a datetime.time object and turn it into today's date

        Args:
            time (datetime.date): time object of when it should start

        Returns:
            Today's date with the time information from the passed
            ``time`` attached
        '''
        tzinfo = time.tzinfo if time.tzinfo else UTC

        return datetime.datetime.today().replace(
            hour=time.hour, minute=time.minute, second=time.second, tzinfo=tzinfo
        )

    def schedule_job(self):
        '''Schedule a job.

        If the time_override param is set to True, it will override the timing.
        This allows us to always run jobs from the tests or manually force a job
        to be scheduled if necessary.

        Returns:
            If all the conditions for scheduling a job are true, a new
            :py:class:`~purchasing.jobs.job_base.JobStatus` model will be created
            or selected and returned.
        '''
        start_time = self.start_time

        if isinstance(self.start_time, datetime.time):
            start_time = self.build_datetime_object(self.start_time)

        if start_time is None or \
            UTC.localize(datetime.datetime.utcnow()) > start_time.astimezone(UTC) or \
                self.time_override is True:

                model, exists = get_or_create(
                    db.session, self.job_status_model, name=self.name,
                    date=datetime.date.today()
                )

                if not exists:
                    model.update(status='new')

                return model, exists

    def run_job(self, job):
        '''Run a job. Must be implemented by subclasses

        Raises:
            NotImplementedError
        '''
        raise NotImplementedError

class EmailJobBase(JobBase):
    def should_run(self):
        return True

    def run_job(self, job):
        if self.should_run():
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
        else:
            job.update(status='skipped')
            return job

    def build_notifications(self):
        raise NotImplementedError
