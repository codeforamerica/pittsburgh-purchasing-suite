# -*- coding: utf-8 -*-

from purchasing.app import celery
from purchasing.extensions import mail, db, cache

from purchasing.data.importer.scrape_county import main as scrape_county

@celery.task
def send_email(messages):
    with mail.connect() as conn:
        for message in messages:
            conn.send(message)

@celery.task
def rebuild_search_view():
    try:
        session = db.create_scoped_session()
        session.execute(
            '''
            REFRESH MATERIALIZED VIEW CONCURRENTLY search_view
            '''
        )
        session.commit()
        db.engine.dispose()
    except Exception, e:
        raise e
    finally:
        cache.delete('refresh-lock')

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
