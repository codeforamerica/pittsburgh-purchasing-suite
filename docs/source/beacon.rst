Beacon
======

Beacon is a tool for City Purchasers to advertise new opportunities and businesses to sign up to receive information about those opportunities. It is divided into two sections: a public-facing section and an administrative section. The public-facing section contains a list and detail view of both currently available and past opportunities, along with overview informational pages, signup pages, and a page to manage email subscriptions.

The administrative section handles the creation and editing of new opportunities along with an approval flow for opportunities.

Additionally, Beacon has two nightly jobs that run: one nightly job sends emails whenever new opportunities become "published" (see :py:class:`~purchasing.opportunities.models.Opportunity` for more information), and a job that runs and sends a bi-weekly update with a list of all non-expired opportunities that have been posted in the past two weeks to all signed-up Vendors. See more in the :ref:`beacon-nightly` section.

Models Used
-----------

* :py:class:`purchasing.opportunities.models.Opportunity`
* :py:class:`purchasing.opportunities.models.OpportunityDocument`
* :py:class:`purchasing.opportunities.models.RequiredBidDocument`
* :py:class:`purchasing.opportunities.models.Vendor`
* :py:class:`purchasing.opportunities.models.Category`

Forms
-----

Forms
^^^^^

.. automodule:: purchasing.opportunities.forms
    :members:

Validators
^^^^^^^^^^

.. automodule:: purchasing.opportunities.validators
    :members:

Helper functions
----------------

.. automodule:: purchasing.opportunities.util
    :members:

Views
-----

Public-facing
^^^^^^^^^^^^^

.. autoflask:: purchasing.app:create_app()
    :blueprints: opportunities
    :undoc-endpoints: opportunities.static

Administration
^^^^^^^^^^^^^^

.. autoflask:: purchasing.app:create_app()
    :blueprints: opportunities_admin
    :undoc-endpoints: opportunities_admin.static

.. _beacon-nightly:

Nightly Jobs
------------

.. automodule:: purchasing.jobs.scout_nightly
    :members:
