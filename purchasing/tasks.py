# -*- coding: utf-8 -*-

from purchasing.app import celery
from purchasing.extensions import mail

@celery.task
def send_email(messages, multi):
    if multi:
        with mail.connect() as conn:
            for message in messages:
                conn.send(message)
    else:
        mail.send(messages[0])
