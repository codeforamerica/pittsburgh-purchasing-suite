# -*- coding: utf-8 -*-

from purchasing.app import celery
from purchasing.extensions import mail, db

from purchasing.data.importer.scrape_county import main as scrape_county

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

@celery.task
def scrape_county_task(job):
    added, skipped = 0, 0
    job.update(status='started')
    try:
        added, skipped = scrape_county()
        job.update(status='success')

    except Exception, e:
        job.update(status='failed', info=str(e))
        raise e
