Scout
=====

Scout is a tool for City Purchasers to search for contract information, including line item information, and subscribe to receive updates when a contract is about to expire. It's functionality revolves around the ever-present Search Form, which is backed by a Postgres Materialized View with full-text search. For more information about how this search is created, please see Full-text Search with Postgres and Sqlalchemy, parts `one <http://bensmithgall.com/blog/full-text-search-flask-sqlalchemy/>`_ and `two <http://bensmithgall.com/blog/full-text-search-sqlalchemy-part-ii/>`_.

Scout also features Contract and Company detail pages, with pricing, detail, and metadata information for contracts and contact information for companies.

.. seealso::

    `How to use Scout <https://docs.google.com/document/d/1hV5_yHKWWgU2qgtPI011cdiWOvXewRJK3v-MaXEXEkA/export?format=pdf>`_, an internal product guide for more information about the user interface and user experience.

Models used
-----------

* :py:class:`purchasing.data.contracts.ContractBase`
* :py:class:`purchasing.data.contracts.ContractType`
* :py:class:`purchasing.data.contracts.ContractProperty`
* :py:class:`purchasing.data.contracts.LineItem`
* :py:class:`purchasing.data.companies.Company`
* :py:class:`purchasing.data.companies.CompanyContact`
* :py:class:`purchasing.users.models.User`

Forms
-----

.. automodule:: purchasing.scout.forms
    :members:

Helpers
-------

.. automodule:: purchasing.scout.util
    :members:

Views
------

.. autoflask:: purchasing.app:create_app()
    :endpoints:
        scout.explore, scout.search, scout.search_feedback, scout.filter_no_department,
        scout.filter, scout.contract, scout.company, scout.feedback, scout.subscribe, scout.unsubscribe

Nightly Jobs
------------

.. automodule:: purchasing.jobs.scout_nightly
    :members:


.. _Sqlalchemy case expressions: http://docs.sqlalchemy.org/en/rel_1_0/core/sqlelement.html?highlight=case#sqlalchemy.sql.expression.case
.. _Sqlalchemy query filters: http://docs.sqlalchemy.org/en/rel_1_0/orm/query.html#sqlalchemy.orm.query.Query.filter
