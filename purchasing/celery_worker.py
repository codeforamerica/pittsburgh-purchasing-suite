import os

from purchasing.app import create_app, celery
from purchasing.settings import DevConfig

app = create_app(os.environ.get('CONFIG', DevConfig))
app.app_context().push()
