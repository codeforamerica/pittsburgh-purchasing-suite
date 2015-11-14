Data Importers
==============

Populating the applications in the suite with data requires a number of import tasks, outlined below.

X-Drive Importer
----------------

Before :doc:`/scout`, City of Pittsburgh commodity contracts lived in a variety of spreadsheets on a shared drive in the City known as the X-Drive. A consolidated final form of this spreadsheet lives in the app's source under ``purchasing/data/importer/files/2015-08-13-contractlist.csv``. This was the switchover date for the City to Scout, meaning that after this date all contract updates were made through Scout.

The X-Drive importer (also known as the old contract importer) is tasked with performing the following actions:

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
4. Use the converted data to look up or create new :py:class:`~purchasing.data.contracts.ContractBase`, with the linked :py:class:`~purchasing.data.companies.Company` from the first step


COSTARS Importer
----------------

Contracts under the Cooperative Sourcing to Achieve Reductions in Spend (COSTARS) agreement servicing Allegheny County (and thus available to City of Pittsburgh purchasers) can be found as numerous downloadable spreadsheets via the `COSTARS website <http://www.dgs.pa.gov/Local%20Government%20and%20Schools/COSTARS/Pages/default.aspx#.VkZs0d-rT2I>`_, but not linked to directly.

The COSTARS Importer is tasked with the following actions:

* Creating new :py:class:`~purchasing.data.companies.Company` objects
* Creating new :py:class:`~purchasing.data.companies.CompanyContact` objects
* Creating new :py:class:`~purchasing.data.contracts.ContractBase` objects
* Creating new :py:class:`~purchasing.data.contracts.LineItem` objects
* Linking all of these entities together as is appropriate
* Handling manufacturer lists and linking them as properties to new Contract objects

The way the importer handles this is roughly as follows:

For each row in COSTARS spreadsheet file:

1. Look up or create (via :py:func:`~purchasing.database.get_or_create`) companies based on their names
2. Look up or create (via the same function as above) company contacts based on their names/addresses/phone/email/etc., linking them with the found or created company from the above step
3. Convert expiration dates, financial ids, contract types to meaningful information for the data model, including looking up or creating new :py:class:`~purchasing.data.contracts.ContractType` objects as necessary
4. Use the converted data to look up or create new :py:class:`~purchasing.data.contracts.ContractBase`, with the linked :py:class:`~purchasing.data.companies.Company` from the first step
5. Check to see if contract has matching PDF file and build URL for View Contract link


NIGP Importer
-------------

Categories for commodities and services used in :doc:`/beacon` are based on the `National Institute for Governmental Purchasing (NIGP) <http://www.nigp.org/eweb/StartPage.aspx>`_ codes. In order to facilitate a more straightforward signup process, codes and descriptions were combined, grouped, and consolidated in ``purchasing/data/importer/files/2015-07-01-nigp-cleaned.csv``.

The NIGP Importer is tasked with the following actions:
* Creating new :py:class:`~purchasing.opportunities.models.Category` objects

The way the importer handles this is roughly as follows:

For each row in NIGP category file:

1. Look up or create (via :py:func:`~purchasing.database.get_or_create`) subcategories based on their names
2. Split up cases of multiple NIGP code or examples into separate rows


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
