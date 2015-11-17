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

.. _costars-importer:

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

.. _nigp-importer:

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

State contracts adopted by the City of Pittsburgh were collected via the `State of Pennsylvania eMarketplace search tool <http://www.emarketplace.state.pa.us/BidContracts.aspx>`_ and live in the app's source under ``purchasing/data/importer/files/2015-10-27-state-contracts.csv``

The State Contract Importer is tasked with the following actions:

* Creating new :py:class:`~purchasing.data.companies.Company` objects
* Creating new :py:class:`~purchasing.data.companies.CompanyContact` objects
* Creating new :py:class:`~purchasing.data.contracts.ContractBase` objects
* Linking all of these entities together as is appropriate
* Handling contract numbers as well as parent contract numbers and linking them as properties to new Contract objects

The way the importer handles this is roughly as follows:

For each row in a given csv file:

1. Look up or create (via :py:func:`~purchasing.database.get_or_create`) companies based on their names.
2. Look up or create (via the same function as above) company contacts based on their names/addresses/phone/email/etc., linking them with the found or created company from the above step
3. Convert expiration dates, financial ids, and contract types to meaningful information for the data model, including looking up or creating new :py:class:`~purchasing.data.contracts.ContractType` objects as necessary
4. Use the converted data to look up or create new :py:class:`~purchasing.data.contracts.ContractBase`, with the linked :py:class:`~purchasing.data.companies.Company` from the first step


County Scraper
--------------

See Also:
    :py:class:`~purchasing.jobs.scout_nightly.CountyScrapeJob`, :py:func:`~purchasing.tasks.scrape_county_task`

The County Scraper attempts to scrape line item information to build :py:class:`~purchasing.data.contracts.LineItem` objects to link with :py:class:`~purchasing.data.contracts.ContractBase` objects. It does this by generating links to all un-scraped contracts and trying to hit those links and parse out the information contained there. The HTML generated on the site is not particularly good (for example, "checked" radio boxes are, in fact, not radio boxes but *images* of radio boxes and tables abound), so the process is a bit brittle.

The scraping is divided into two distinct steps:

1. From the main page of all contracts, build links to all of the individual contract pages. Because these follow a regular server-generated pattern, it is much faster to build them internally instead of trying to scrape them out of the HTML.
2. For each of the generated links, go through and try to parse out individual line items:

    a. Get the contract object to append line items to based on the contract description and the IFB (spec) number (see :py:meth:`~purchasing.data.contracts.ContractBase.get_spec_number` for more information on spec numbers).
    b. Using `Beautiful Soup <http://www.crummy.com/software/BeautifulSoup/>`_, we go through an individual page of awards and pull out the line items. Note that we have to deal with some pretty non-compliant HTML (including unclosed table tags and an early-terminating form tag), which makes this a bit trickier. The basic method is:

        1. Get all of the tables on the page
        2. Exclude "metadata" tables (the first five and last table)
        3. From this point, the tables alternate: "item" tables are tables that contain line items. "Award" tables are tables that contain information about the awarded company of the previous item. This mean that we need to parse two tables to get the full information about a single line item.
    c. Once we have both the line item information and the award information for each line item contained in an individual page, we are able to create the :py:class:`~purchasing.data.contracts.LineItem` object and try to find the relevant company for that line item as well.

Stages and Flows
----------------

Contracts in :doc:`/conductor` are moved through stages according to the flows they are a part of. These are created via the admin interface, but are seeded for development with this importer.

The Stages and Flows seed task is tasked with the following actions:

* Creating three new :py:class:`~purchasing.data.stages.Stage` objects
* Creating one new :py:class:`~purchasing.data.flows.Flow` object
* Linking these entities together as is appropriate

The way the seed task handles this is roughly as follows:

1. Create three new stages
2. Create one new flow and seed with the new stages arranged in order


Importer Utilities
------------------

All of the importers described above share some common utilities, which are discussed here:

.. automodule:: purchasing.data.importer.importer
    :members:
