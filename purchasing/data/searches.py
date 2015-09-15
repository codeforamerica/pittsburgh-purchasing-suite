# -*- coding: utf-8 -*-

import datetime

from purchasing.database import db, Model, Column
from sqlalchemy.dialects.postgresql import TSVECTOR
from purchasing.data.contracts import ContractBase

class SearchView(Model):
    '''search_view is a materialized view with all of our text columns
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

def add_archived_filter(contracts, archived):

    contracts = contracts.filter(
        ContractBase.financial_id != None,
        ContractBase.expiration_date != None,
        SearchView.expiration_date != None
    )

    if not archived:
        contracts = contracts.filter(
            ContractBase.is_archived == False,
            ContractBase.expiration_date >= datetime.date.today(),
        )

    return contracts

def find_contract_metadata(search_term, case_statements, filter_or, filter_and, archived=False):
    '''
    Takes a search term, case statements, and filter clauses and
    returns out a list of result objects including contract id,
    company id, financial id, expiration date, awarded name
    '''

    rank = db.func.max(db.func.full_text.ts_rank(
        db.func.setweight(db.func.coalesce(SearchView.tsv_company_name, ''), 'A').concat(
            db.func.setweight(db.func.coalesce(SearchView.tsv_contract_description, ''), 'A')
        ).concat(
            db.func.setweight(db.func.coalesce(SearchView.tsv_detail_value, ''), 'D')
        ).concat(
            db.func.setweight(db.func.coalesce(SearchView.tsv_line_item_description, ''), 'B')
        ), db.func.to_tsquery(search_term, postgresql_regconfig='english')
    ))

    contracts = db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'),
        SearchView.company_id, SearchView.contract_description,
        SearchView.financial_id, SearchView.expiration_date,
        SearchView.company_name, db.case(case_statements).label('found_in'),
        rank.label('rank')
    ).join(
        ContractBase, ContractBase.id == SearchView.contract_id
    ).filter(
        db.or_(
            db.cast(SearchView.financial_id, db.String) == search_term,
            *filter_or
        ),
        *filter_and
    ).group_by(
        SearchView.contract_id,
        SearchView.company_id,
        SearchView.contract_description,
        SearchView.financial_id,
        SearchView.expiration_date,
        SearchView.company_name,
        db.case(case_statements)
    ).order_by(
        db.text('rank DESC')
    )

    contracts = add_archived_filter(contracts, archived)

    return contracts.all()

def return_all_contracts(filter_and, archived=False):
    contracts = db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'), SearchView.company_id,
        SearchView.contract_description, SearchView.financial_id,
        SearchView.expiration_date, SearchView.company_name
    ).join(ContractBase, ContractBase.id == SearchView.contract_id).filter(
        *filter_and
    )

    contracts = add_archived_filter(contracts, archived)

    return contracts.all()
