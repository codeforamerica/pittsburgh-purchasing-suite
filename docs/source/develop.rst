Developing
==========

Core Dependencies
^^^^^^^^^^^^^^^^^

The purchasing suite is a `Flask`_ app. It uses `Postgres`_ for a database and uses `bower`_ to manage most of its dependencies. It also uses `less`_ to compile style assets. In production, the project uses `Celery`_ with `Redis`_ as a broker to handle backgrounding various tasks. Big thanks to the `cookiecutter-flask`_ project for a nice kickstart.

It is highly recommended that you use use `virtualenv`_ (and `virtualenvwrapper`_ for convenience). For a how-to on getting set up, please consult this `virtualenv howto <https://github.com/codeforamerica/howto/blob/master/Python-Virtualenv.md>`_. Additionally, you’ll need node to install bower (see this `node howto <https://github.com/codeforamerica/howto/blob/master/Node.js.md>`_ for more on Node), and it is recommended that you use `postgres.app`_ to
handle your Postgres (assuming you are developing on OSX).

Installation and setup
^^^^^^^^^^^^^^^^^^^^^^

Quick local installation using Make
'''''''''''''''''''''''''''''''''''

First, create a virtualenv and activate it. Then:

.. code:: bash

    git clone git@github.com:codeforamerica/pittsburgh-purchasing-suite.git
    # create the 'purchasing' database
    psql -c 'create database purchasing;'
    # set environmental variables - it is recommended that you set these for your
    # your virtualenv, using a tool like autoenv or by modifying your activate script
    export ADMIN_EMAIL='youremail@someplace.net'
    export CONFIG=purchasing.settings.DevConfig
    # this next command will do all installs, add tables to the database,
    # and insert seed data (note that this needs an internet connection to
    # scrape data from Allegheny County)
    make setup
    # start your server
    python manage.py server

More detailed installation instructions
'''''''''''''''''''''''''''''''''''''''

If you want to walk through the complete setup captured above in ``make setup``, use the following commands to bootstrap your development environment:

Python app:
"""""""""""

.. code:: bash

    # clone the repo
    git clone https://github.com/codeforamerica/pittsburgh-purchasing-suite
    # change into the repo directory
    cd pittsburgh-purchasing-suite
    # install python dependencies
    # NOTE: if you are using postgres.app, you will need to make sure to
    # set your PATH to include the bin directory. For example:
    # export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.4/bin/
    pip install -r requirements/dev.txt
    # note, if you are looking to deploy, you won't need dev dependencies.
    # uncomment & run this command instead:
    # pip install -r requirements.txt

.. note:: The app’s configuration lives in ``purchasing/settings.py``. When different configurations (such as ``DevConfig``) are referenced in the next sections, they are contained in that file.

Email:
""""""

The app uses `Flask-Mail`_ to handle sending emails. This includes emails about subscriptions to various contracts, notifications about contracts being followed, and others. In production, the app relies on `Sendgrid`_, but in development, it uses the `Gmail SMTP server`_. If you don’t need to send emails, you can disable emails by setting ``MAIL_SUPPRESS_SEND = True`` in the ``DevConfig`` configuration object.

If you would like to send email over the Gmail SMTP server, you will need to add two environmental variables: ``MAIL_USERNAME`` and ``MAIL_PASSWORD``. You can use Google’s `app passwords`_ to create a unique password only for the app.

Database:
"""""""""

.. code:: bash

    # login to postgres. If you are using postgres.app, you can click
    # the little elephant in your taskbar to open this instead of using
    # psql
    psql
    create database purchasing;

Once you’ve created your database, you’ll need to open ``purchasing/settings.py`` and edit the ``DevConfig`` object to use the proper `SQLAlchemy database configuration string`_. If you named your database ``purchasing``, you probably won’t have to change anything. Then:

.. code:: bash

    # upgrade your database to the latest version
    python manage.py db upgrade

By default, SQLAlchemy logging is turned off. If you want to enable it, you’ll need to add a ``SQLALCHEMY_ECHO`` flag to your environment.

Front-end:
""""""""""

If you haven’t installed `npm`_, please consult this `howto <https://github.com/codeforamerica/howto/blob/master/Node.js.md>`_ for the best way to do so. On Mac, you can also use `homebrew`_.

Once you install node, run the following:

.. code:: bash

    # install bower, less, and uglifyjs
    # you may need to use sudo
    npm install
    # use bower to install the dependencies
    bower install

Login and user accounts
"""""""""""""""""""""""

Right now, the Pittsburgh Purchasing Suite uses `persona`_ to handle authentication. The app uses its own user database to manage roles and object-based authorization. You will need to sign in through persona and then enter yourself into the database in order to have access to admin and other pages.

A manage task has been created to allow you to quickly create a user to access the admin and other staff-only tasks. To add an email, run the following command (NOTE: if you updated your database as per above, you will probably want to give youself a role of 1, which will give you superadmin privledges), putting your email/desired role in the appropriate places:

.. code:: bash

    python manage.py seed_user -e <your-email-here> -r <your-desired-role>

Now, logging in through persona should also give you access to the app.

Up and running
""""""""""""""

If you boot up the app right now, it will have no data. If you want to add some data, a small manage task has been added to allow for quick data importation.

.. code:: bash

    # run the data importers
    python manage.py seed

Now you should be ready to roll with some seed data to get you started!

.. code:: bash

    # run the server
    python manage.py server

Celery and Redis
""""""""""""""""

To get started with development, you won’t need to do any additional setup. However, if you want to emulate the production environment on your local system, you will need to install Redis and configure Celery. To do everything, you’ll need to run Redis (our broker), Celery (our task queue), and the app itself all at the same time.

Get started by installing redis. On OSX, you can use `homebrew`_:

.. code:: bash

    brew install redis

Once this is all installed, you should see a handy command you can use to start the Redis cluster locally (something like the following):

.. code:: bash

    redis-server /usr/local/etc/redis.conf

Now, redis should be up and running. Before we launch our web app, we’ll need to configure it to use our Celery/Redis task queue as opposed to using the `eager fake queue`_. Navgate to ``purchasing/settings.py``. In the ``DevConfig``, there should be three settings related to Celery. Commenting out ``CELERY_ALWAYS_EAGER`` and un-commenting ``CELERY_BROKER_URL`` and ``CELERY_RESULT_BACKEND`` will signal the app to use Redis for Celery’s broker.

At this point, you’ll be abel to boot up the celery worker. Our app’s celery workers live in ``purchasing/celery_worker.py``. Start them as follows:

.. code:: bash

    celery --app=purchasing.celery_worker:celery worker --loglevel=debug

You can log at a higher level than debug (info, for example), if you want to get fewer messages. Finally, we’ll need to start our web app. You can do this as normal:

.. code:: bash

    python manage.py server

When all of these are running, you should be ready to go!

Testing
^^^^^^^

In order to run the tests, you will need to create a test database. You can follow the same procedures outlined in the install section. By default, the database should be named ``purchasing_test``:

.. code:: bash

    psql
    create database purchasing_test;

Tests are located in the ``purchasing_test`` directory. To run the tests, run

.. code:: bash

    PYTHONPATH=. nosetests purchasing_test/

from inside the root directory. For more coverage information, run

.. code:: bash

    PYTHONPATH=. nosetests purchasing_test/ -v --with-coverage --cover-package=purchasing_test --cover-erase

.. _Flask: http://flask.pocoo.org/
.. _Postgres: http://www.postgresql.org/
.. _bower: http://bower.io/
.. _less: http://lesscss.org/
.. _Celery: http://celery.readthedocs.org/en/latest/
.. _Redis: http://redis.io/
.. _cookiecutter-flask: https://github.com/sloria/cookiecutter-flask
.. _virtualenv: https://readthedocs.org/projects/virtualenv/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.org/en/latest/
.. _postgres.app: http://postgresapp.com/
.. _Flask-Mail: https://pythonhosted.org/Flask-Mail/
.. _Sendgrid: https://sendgrid.com/
.. _Gmail SMTP server: https://support.google.com/a/answer/176600?hl=en
.. _app passwords: https://support.google.com/accounts/answer/185833?hl=en
.. _SQLAlchemy database configuration string: http://docs.sqlalchemy.org/en/rel_1_0/core/engines.html#postgresql
.. _npm: https://www.npmjs.com/
.. _homebrew: http://brew.sh/
.. _persona: https://login.persona.org/about
.. _eager fake queue: http://celery.readthedocs.org/en/latest/configuration.html#celery-always-eager
