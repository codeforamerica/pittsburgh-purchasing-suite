# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.data.models import Company, ContractBase
from purchasing.data.contracts import get_one_contract

def create_new_company(company_data):
    '''
    Creates a new company and returns that company.
    '''
    try:
        assign_contract_to_company(company_data.get('contracts', []))
        company = Company.create(**company_data)
        return company
    except Exception, e:
        db.session.rollback()
        raise e

def update_company(company_id, company_data):
    '''
    Updates an individual company and returns that company
    '''
    try:
        company = get_one_company(company_id)
        assign_contract_to_company(company_data.get('contracts', []))
        company.update(**company_data)
        return company
    except Exception, e:
        db.session.rollback()
        raise e

def delete_company(company_id):
    company = get_one_company(company_id)
    company.delete()
    return True

def get_one_company(company_id):
    '''
    Returns a company associated with a company ID
    '''
    return Company.query.get(company_id)

def get_all_companies():
    '''
    Returns a list of companies.
    TODO: Paginate these results.
    '''
    return Company.query.all()

def get_all_companies_query():
    return Company.query

def assign_contract_to_company(contracts_list):
    for ix, contract in enumerate(contracts_list):
        if isinstance(contract, ContractBase):
            pass
        elif isinstance(contract, int):
            contracts_list[ix] = get_one_contract(contract)
        else:
            raise Exception('Contract must be a Contract object or a contract id')

    return contracts_list
