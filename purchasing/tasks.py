# -*- coding: utf-8 -*-

from purchasing.app import celery
from purchasing.extensions import mail, db

@celery.task
def send_email(messages, multi):
    if multi:
        with mail.connect() as conn:
            for message in messages:
                conn.send(message)
    else:
        mail.send(messages[0])

@celery.task
def rebuild_search_view():
    session = db.create_scoped_session()
    session.execute(
        '''
        REFRESH MATERIALIZED VIEW CONCURRENTLY search_view
        '''
    )
    session.commit()
    db.engine.dispose()
