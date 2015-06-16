# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.data.models import SearchView

def find_contract_metadata(search_term, case_statements, filter_clauses):
    '''
    Takes a search term, case statements, and filter clauses and
    returns out a list of result objects including contract id,
    company id, financial id, expiration date, awarded name
    '''
    contracts = db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'),
        SearchView.company_id,
        SearchView.contract_description,
        SearchView.financial_id,
        SearchView.expiration_date,
        SearchView.company_name,
        db.case(case_statements).label('found_in'),
        db.func.max(db.func.full_text.ts_rank(
            db.func.setweight(db.func.coalesce(SearchView.tsv_company_name, ''), 'A').concat(
                db.func.setweight(db.func.coalesce(SearchView.tsv_contract_description, ''), 'D')
            ).concat(
                db.func.setweight(db.func.coalesce(SearchView.tsv_detail_value, ''), 'D')
            ).concat(
                db.func.setweight(db.func.coalesce(SearchView.tsv_line_item_description, ''), 'B')
            ), db.func.to_tsquery(search_term, postgresql_regconfig='english')
        )).label('rank')
    ).filter(db.or_(
        db.cast(SearchView.financial_id, db.String) == search_term,
        *filter_clauses
    )).group_by(
        SearchView.contract_id,
        SearchView.company_id,
        SearchView.contract_description,
        SearchView.financial_id,
        SearchView.expiration_date,
        SearchView.company_name,
        db.case(case_statements)
    ).order_by(
        db.text('rank DESC')
    ).all()

    return contracts

def return_all_contracts():
    return db.session.query(
        db.distinct(SearchView.contract_id).label('contract_id'), SearchView.company_id,
        SearchView.contract_description, SearchView.financial_id,
        SearchView.expiration_date, SearchView.company_name
    ).all()
