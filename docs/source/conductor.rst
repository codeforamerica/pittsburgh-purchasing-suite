Conductor
=========

Conductor is a tool for the Office of Management and Budget (OMB) to manage contracts as they move through the city's various processes for renewal, rebid, extension, etc. From the user's perspective, the way this works is that they define different :py:class:`~purchasing.data.flows.Flow` objects that are comprised of an ordered array of :py:class:`~purchasing.data.stages.Stage` objects. :py:class:`~purchasing.data.contracts.ContractBase` objects are then assigned to a :py:class:`~purchasing.users.models.User` and a :py:class:`~purchasing.data.flows.Flow`. At this point, the :py:class:`~purchasing.data.contract_stages.ContractStage` are all created, and the contract is essentially on rails. The "Conductor", then, is the person who drives this contract through the various stages towards completion.

Once a contract is in progress, Conductors complete various stages by marking them as such in the UI. They can also perform various actions in each stage, including making notes, sending emails to different people interested in the process, change metadata about the contract, and adverstise through a new Opportunity on :doc:`beacon`.

Models Used
-----------

* :py:class:`purchasing.data.contracts.ContractBase`
* :py:class:`purchasing.data.contracts.ContractProperty`
* :py:class:`purchasing.data.companies.Company`
* :py:class:`purchasing.data.companies.CompanyContact`
* :py:class:`purchasing.data.stages.Stage`
* :py:class:`purchasing.data.flows.Flow`
* :py:class:`purchasing.data.contract_stages.ContractStage`
* :py:class:`purchasing.data.contract_stages.ContractStageActionItem`
* :py:class:`purchasing.opportunities.models.Opportunity`
* :py:class:`purchasing.users.models.User`

Forms
-----

Forms
^^^^^

.. automodule:: purchasing.conductor.forms
    :members:

Validators
^^^^^^^^^^

.. automodule:: purchasing.conductor.validators
    :members:

Helper Methods
--------------

.. automodule:: purchasing.conductor.util
    :members:

Views
-----

Main
^^^^

.. autoflask:: purchasing.app:create_app()
   :blueprints: conductor
   :undoc-endpoints: conductor.static

.. _conductor-uploads:

Uploads
^^^^^^^

.. autoflask:: purchasing.app:create_app()
   :blueprints: conductor_uploads
   :undoc-endpoints: conductor_uploads.static

Metrics
^^^^^^^

.. autoflask:: purchasing.app:create_app()
   :blueprints: conductor_metrics
   :undoc-endpoints: conductor_metrics.static

.. _FileStorage: http://werkzeug.pocoo.org/docs/0.10/datastructures/#werkzeug.datastructures.FileStorage

