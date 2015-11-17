Redeploying
===========

The Pittsburgh Purchasing Suite is built primarily on top of three key services: **Heroku**, **AWS S3**, and **Sendgrid** (though the email delivery service is fairly agnostic, as will be discussed later). Building out a production-level version of the Pittsburgh Purchasing Suite involves configuring these services and setting up some key environment variables via the Heroku UI.

Provisioning Services
---------------------

Heroku
^^^^^^

.. pull-quote::

    Heroku is a cloud platform based on a managed container system, with integrated data services and a powerful ecosystem, for deploying and running modern apps. The Heroku developer experience is an app-centric approach for software delivery, integrated with today’s most popular developer tools and workflows.

`Heroku <https://www.heroku.com/>`_ is a Platform as a Service (PaaS) that simplifies deployment and production server management. The Pittsburgh Purchasing Suite runs on top of Heroku. It uses web processes to handle web requests, worker processes to handle sending emails (see :py:class:`~purchasing.notifications.Notification`), rebuilding the search index (see :py:class:`~purchasing.database.RefreshSearchViewMixin`), and other background tasks. It also uses the `Heroku scheduler <https://elements.heroku.com/addons/scheduler>`_ add-on to do nightly jobs (see :ref:`nightly-jobs`).

The base Heroku requirements involve `Heroku Postgres <https://www.heroku.com/postgres>`_ and `Heroku Redis <https://elements.heroku.com/addons/heroku-redis>`_. Redeploying a version as it currently exists requires both of these as dependencies.

AWS S3
^^^^^^

.. pull-quote::

    Amazon Simple Storage Service (Amazon S3), provides developers and IT teams with secure, durable, highly-scalable object storage. Amazon S3 is easy to use, with a simple web service interface to store and retrieve any amount of data from anywhere on the web.

`S3 <https://aws.amazon.com/s3/>`_ is a storage services used to store PDF documents, specifically .pdf versions of the contracts themselves, along with documents that exist to support opportunities. S3 also stores all static assets (img/js/css) for the application. By default, uploaded documents have aggressive caching headers and the maximum expiry set dates.

Sendgrid
^^^^^^^^

.. pull-quote::

    SendGrid is a cloud-based SMTP provider that allows you to send email without having to maintain email servers. SendGrid manages all of the technical details, from scaling the infrastructure to ISP outreach and reputation monitoring to whitelist services and real time analytics.

`Sendgrid <https://sendgrid.com/>`_ is an email provider that gives hooks for web-based and SMTP-based email. The suite uses `Flask Mail <https://pythonhosted.org/Flask-Mail/>`_. Because of this, you should be able to swap out any similar email provider (such as Mandrill, etc.) and get similar functionality as long as you update the ``MAIL_USERNAME`` and ``MAIL_PASSWORD`` environment variables.

Configuring the Environment
---------------------------

In order to deploy the Pittsburgh Purchasing Suite, the following environmental variables must be set via the Heroku settings page. For more information, see `this heroku guide <https://devcenter.heroku.com/articles/config-vars>`_.

* ``SECRET_KEY``

    The secret key protects the app's session, forms, and other pieces. For more information about how Flask uses secret keys, please look at `this stack overflow answer <http://stackoverflow.com/a/22463969>`_. To generate a secret key, you can run the following snippet directly from bash:

    .. codeblock::

        python -c "import os; print os.urandom(24).encode('hex')"

    Take that and input it as the value to the ``SECRET_KEY``

* ``BROWSERID_URL``

    The app uses `persona <https://login.persona.org/>`_ to manage authentication (see :ref:`persona` for more). ``BROWSERID_URL`` is domain to send over to Persona to validate that people are logging into the right machine. For local development, this will be ``127.0.0.1:9000``, and for production, it should match whatever users see in their address bar.

* ``MAIL_DEFAULT_SENDER``

    The default from email address that will be used for sending out emails -- if nothing is provided from the environment, this will default to to ``no-reply@buildpgh.com``.

* ``BEACON_SENDER``

    The default from email address that will be used for sending out emails through :doc:`/beacon`. If nothing is provided from the environment, this will default to ``beaconbot@buildpgh.com``.

* ``CONDUCTOR_SENDER``

    The default from email address that will be used for sending out emails through :doc:`/beacon`. If nothing is provided from the environment, this will default to ``conductorbot@buildpgh.com``.

* ``MAX_CONTENT_LENGTH``

    The maximum file size for files to be uploaded. This defaults to 2MB.

* ``UPLOAD_FOLDER``

    The upload directory is the temporary home for uploaded conductor COSTARS files (see :ref:`conductor-uploads`).

* ``S3_BUCKET_NAME``

    The `bucket <http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html>`_ name for Amazon S3 files (which will hold static assets like CSS/JS). No default.

* ``AWS_ACCESS_KEY_ID``

    Your username for your AWS account. For more information, see `AWS IAM documentation <https://aws.amazon.com/iam/>`_

* ``AWS_SECRET_ACCESS_KEY``

    Your password for your AWS account. For more information, see `AWS IAM documentation <https://aws.amazon.com/iam/>`_

* ``SERVER_NAME``

    The name and port number of the server. For more, see the `Flask documentation on SERVER_NAME <http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values>`_.

* ``DISPLAY_TIMEZONE``

    A timezone string that will be used for display times across the application. This must be a valid pytz string, which is a highly exhaustive list. For more, see `the pytz docs <http://pytz.sourceforge.net/#helpers>`_.

* ``EXTERNAL_LINK_WARNING``

    For `dotgov.gov compliance <https://www.dotgov.gov/portal/web/dotgov/program-guidelines>`_, links to external sites must be flagged with a small alert letting people know they are leaving the site. This is a boolean flag as to whether this should be enabled or disabled. Defaults to False.

* ``DATABASE_URL``

    The link to the database. If Herkou is being used, this value will be set automatically.

* ``MAIL_USERNAME``

    The username to the mail send service being used. If using a service like Sendgrid, this can be configured as a separate custom account from the accounts dashboard.

* ``MAIL_PASSWORD``

    The password to the mail send service being used.

* ``CELERY_BROKER_URL``

    The URL to the celery broker that will handle the offline jobs. Defaults to ``REDIS_URL``, a value provided by Heroku redis. Other brokers can be used (such as, for example, RabbitMQ or others). For more information about that, take a look at the `celery documentation <http://celery.readthedocs.org/en/latest/getting-started/brokers/index.html#broker-overview>`_

* ``CELERY_RESULT_BACKEND``

    The location of where to store the results from any celery long-running tasks.

* ``CACHE_REDIS_URL``

    The Redis URL for `Flask Cache <https://pythonhosted.org/Flask-Cache/>`_. By default, this will ``REDIS_URL`` as set from Heroku. If you want to use a different cache, place that URL in the environment.
