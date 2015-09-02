web: newrelic-admin run-program gunicorn purchasing.app:create_app\($CONFIG\) -b 0.0.0.0:$PORT -w 3
worker: celery --app=purchasing.celery_worker:celery worker --loglevel=debug
