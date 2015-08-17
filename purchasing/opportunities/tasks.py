# -*- coding: utf-8 -*-

from celery import Celery
from purchasing.app import create_app

# http://flask.pocoo.org/docs/0.10/patterns/celery/
def make_celery(app=None):
    app = app if app else create_app()
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
