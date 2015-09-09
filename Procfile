web: echo $PATH; newrelic-admin run-program gunicorn 'purchasing.app:create_app()' -b 0.0.0.0:$PORT -w 2 --log-file=-
worker: celery --app=purchasing.celery_worker:celery worker --loglevel=debug -Ofair
