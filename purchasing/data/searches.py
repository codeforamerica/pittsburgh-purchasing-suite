# -*- coding: utf-8 -*-

import datetime

from purchasing.database import db
from purchasing.data.models import SearchView, ContractBase

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

def find_contract_metadata(search_term, case_statements, filter_clauses, archived=False):
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
            *filter_clauses
        )
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

def return_all_contracts(archived=False):
    contracts = db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'), SearchView.company_id,
        SearchView.contract_description, SearchView.financial_id,
        SearchView.expiration_date, SearchView.company_name
    ).join(ContractBase, ContractBase.id == SearchView.contract_id)

    contracts = add_archived_filter(contracts, archived)

    return contracts.all()
