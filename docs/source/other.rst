Other Components
================

Notifications
-------------

.. automodule:: purchasing.notifications
    :members:

.. _nightly-jobs:

Nightly Jobs
------------

.. autoclass:: purchasing.jobs.job_base.JobBase
    :members:

.. autoclass:: purchasing.jobs.job_base.EmailJobBase
    :members:

Admin
-----

For more information on how to use the admin, see the `Admin user's guide <https://docs.google.com/document/d/1fjPSmQxTxIkvcOT5RjtG69_oRFDoZGdOdcbQd85C3aI/export?format=pdf>`_. The admin is built using `Flask Admin <https://flask-admin.readthedocs.org/en/latest/>`_.

.. _persona:

Persona
-------

Right now, the Pittsburgh Purchasing Suite uses `Mozilla persona <https://login.persona.org/about>`_ to handle authentication. The app uses its own user database to manage roles and object-based authorization. You will need to sign in through persona and then enter yourself into the database in order to have access to admin and other pages.

Persona uses a two-step system for authentication. The user enters their information into a pop-up box rendered. That information is sent to the Persona system as an ajax request. Persona then returns a JSON response which contains an encoded "assertion". That assertion is passed along to the server. The server then takes that the "assertion" and re-sends it out to persona along with an "audience" key, which refers to the domain of the current request. That request then returns a JSON dictionary which includes the status of the request along with the email address of the person. From there, ensure that they have proper access (managed via the :py:class:`~purchasing.public.models.AcceptedEmailDomains`) model. If everything matches, we log the user in and proceed.

.. _FileStorage: http://werkzeug.pocoo.org/docs/0.10/datastructures/#werkzeug.datastructures.FileStorage
.. _Message: https://pythonhosted.org/Flask-Mail/#flask_mail.Message
