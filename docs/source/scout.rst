Scout
=====


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
    :endpoints: scout.explore, scout.search, scout.search_feedback, scout.filter_no_department, scout.filter, scout.contract, scout.company, scout.feedback, scout.subscribe, scout.unsubscribe


.. _Sqlalchemy case expressions: http://docs.sqlalchemy.org/en/rel_1_0/core/sqlelement.html?highlight=case#sqlalchemy.sql.expression.case
.. _Sqlalchemy query filters: http://docs.sqlalchemy.org/en/rel_1_0/orm/query.html#sqlalchemy.orm.query.Query.filter
