Data Importers
==============

Populating the applications in the suite with data requires a number of import tasks, outlined below.

X-Drive Importer
----------------

Before :doc:`/scout`, contracts lived in a variety of spreadsheets on a shared drive in the City known as the X-Drive. A consolidated final form of this spreadsheet lives in the app's source under ``purchasing/data/importer/files/2015-08-13-contractlist.csv``. This was the switchover date for the City to Scout, meaning that after this date all contract updates were made through Scout.

The X-Drive importer (also known as the old contract importer) is tasked with performing the following tasks:

* Creating new :py:class:`~purchasing.data.companies.Company` objects
* Creating new :py:class:`~purchasing.data.companies.CompanyContact` objects
* Creating new :py:class:`~purchasing.data.contracts.ContractBase` objects
* Linking all of these entities together as is appropriate
* Handling spec numbers where applicable and linking them as properties to new Contract objects

The way the importer handles this is roughly as follows:

For each row in a given csv file:
1. Look up or create (via :py:func:`~purchasing.database.get_or_create`) companies based on their names.
2. Look up or create (via the same function as above) company contacts based on their names/addresses/phone/email/etc., linking them with the found or created company from the above step
3. Convert expiration dates, financial ids, and contract types to meaningful information for the data model, including looking up or creating new :py:class:`~purchasing.data.contracts.ContractType` objects as necessary
4. Use the converted data to look up or create new :py:class:`~purchasing.data.contracts.ContractBase`, with the linked :py:class:`~purchasing.data.companies.Company` from step 1.

COSTARS Importer
----------------

.. _nigp-importer:

NIGP Importer
-------------

Todo:
    Include a link to the NIGP code spreadsheet

State Contract Importer
-----------------------

County Scraper
--------------

Stages and Flows
----------------

Importer Utilities
------------------

All of the importers described above share some common utilities, which are discussed here:

.. automodule:: purchasing.data.importer.importer
    :members:
