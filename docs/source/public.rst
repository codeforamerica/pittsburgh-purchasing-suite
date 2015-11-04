Public & users
==============

Models used
-----------

* :py:class:`purchasing.users.models.User`
* :py:class:`purchasing.users.models.Role`
* :py:class:`purchasing.users.models.Department`
* :py:class:`purchasing.public.models.AppStatus`
* :py:class:`purchasing.public.models.AcceptedEmailDomains`


Forms
-----

.. automodule:: purchasing.users.forms
    :members:

Views
-----

.. autoflask:: purchasing.app:create_app()
   :blueprints: public, users
