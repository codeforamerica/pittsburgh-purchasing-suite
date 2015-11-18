# -*- coding: utf-8 -*-

from purchasing.database import db, Model, Column
from sqlalchemy.dialects.postgresql import TSVECTOR

class SearchView(Model):
    '''SearchView is a materialized view with all of our text columns

    See Also:
        For more detailed information about how this materialized view
        is set up, please refer to `Multi-Table Full Text Search with Postgres,
        Flask, and Sqlalchemy (Part I)
        <http://bensmithgall.com/blog/full-text-search-flask-sqlalchemy/>`_.

        For more information about Postgres Full-text search and TSVectors, refer to
        the `Postgres documentation about full-text search
        <http://www.postgresql.org/docs/current/static/textsearch-intro.html>`_

    Attributes:
        id: Primary key unique ID for result
        contract_id: Unique ID for one contract
        company_id: Unique ID for one company
        financial_id: Financial ID for a contract
        expiration_date: Date a contract expires
        contract_description: Description of the goods or services
            provided by a :py:class:`~purchasing.data.contracts.ContractBase`
        tsv_contract_description: `TSVECTOR`_ of the contract description
        company_name: Name of the company providing services from the
            :py:class:`~purchasing.data.companies.Company` model
        tsv_company_name: `TSVECTOR`_ of the company name
        detail_key: :py:class:`~purchasing.data.contracts.ContractProperty` key
        detail_value: :py:class:`~purchasing.data.contracts.ContractProperty` value
        tsv_detail_value: `TSVECTOR`_ of the detail_value
        line_item_description: Description of a line item from the
            :py:class:`~purchasing.data.contracts.LineItem` model
        tsv_line_item_description: `TSVECTOR`_ of the line item description

    '''
    __tablename__ = 'search_view'

    id = Column(db.Text, primary_key=True, index=True)
    contract_id = Column(db.Integer)
    company_id = Column(db.Integer)
    financial_id = Column(db.String(255))
    expiration_date = Column(db.Date)
    contract_description = Column(db.Text)
    tsv_contract_description = Column(TSVECTOR)
    company_name = Column(db.Text)
    tsv_company_name = Column(TSVECTOR)
    detail_key = Column(db.Text)
    detail_value = Column(db.Text)
    tsv_detail_value = Column(TSVECTOR)
    line_item_description = Column(db.Text)
    tsv_line_item_description = Column(TSVECTOR)
