# -*- coding: utf-8 -*-

import datetime
from purchasing.database import Model, db, get_or_create

import pytz

EASTERN = pytz.timezone('US/Eastern')
UTC = pytz.UTC

class JobStatus(Model):
    '''Model to track nightly job status and reporting

    JobStatus has a primary compound key of name + date

    Attributes:
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

    Attributes:
        jobs: jobs is a list of all jobs currently registered against the JobBase.

    Arguments:
        name: the name instance variable is just the class name of the job.
            This allows us to ensure that we only every have one copy of a
            job scheduled per day.
        time_override: Boolean of whether to override the ``start_time`` parameter
            when scheduling jobs (used primarily in testing)
    '''
    def __init__(self, time_override=False):
        self.name = self.__class__.__name__
        self.time_override = time_override

    jobs = []

    @classmethod
    def register(cls, subcl):
        '''decorator to allow for explicit job registration

        Example:
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
        '''Returns the job status model to be used for the particular job.

        In production, we use the :py:class:`purchasing.jobs.job_base.JobStatus`
        model, but in testing we can overwrite this.
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
        to be scheduled if necessary. In order to schedule a job, one of the
        following conditions must be met:

        1. ``start_time`` is none
        2. The current time is after the ``start_time``
        3. The ``time_override`` attribute is set to True

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
    '''Base job for email alerting/updating

    See Also:
        :py:class:`purchasing.notifications.Notification`
    '''
    def should_run(self):
        '''If a job is scheduled, it should always run.

        This method can be overwritten in the child classes, but
        in the base case, it should always run.

        Returns:
            True
        '''
        return True

    def run_job(self, job):
        '''Run the email job.

        To run an email job, we do the following things:

        1. Set the job status to "started"
        2. Call the :py:func:`~purchasing.jobs.job_base.EmailJobBase.build_notifications`
           method to get a list of notification batches to send
        3. For each batches of notifications to send, try to send them
        4. If at any point we fail, update the status to 'failed',
           and provide additional information
        5. If all notifications send successfully, update the status to 'success'

        Arguments:
            job: :py:class:`~purchasing.jobs.job_base.JobStatus` object

        Returns:
            :py:class:`~purchasing.jobs.job_base.JobStatus`: Job object, modified
                with a new status and any appropriate messages
        '''
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
        '''Method to build Notification objects to send

        Raises
            NotImplementedError
        '''
        raise NotImplementedError
