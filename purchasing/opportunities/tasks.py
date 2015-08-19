# -*- coding: utf-8 -*-

from purchasing.app import celery

@celery.task
def something():
    return 1 + 1
