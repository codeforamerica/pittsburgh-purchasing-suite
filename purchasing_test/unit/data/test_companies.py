# -*- coding: utf-8 -*-

from sqlalchemy.exc import IntegrityError

from purchasing.database import db
from purchasing.data.companies import (
    create_new_company, update_company,
    delete_company, get_all_companies
)
from purchasing.data.models import Company, ContractBase

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_contract, insert_a_company
)

class CompanyTest(BaseTestCase):
    def test_create_new_company(self):
        # assert that creating a normal company should work
        company_data = dict(
            company_name='company one'
        )

        company = create_new_company(company_data)
        self.assertEquals(
            Company.query.first().company_name,
            company.company_name
        )

        # assert that creating a company with an
        # existing contract should work
        contract = insert_a_contract()
        company_with_contract_data = dict(
            company_name='company two',
            contracts=[contract]
        )
        create_new_company(company_with_contract_data)
        self.assertEquals(Company.query.count(), 2)
        self.assertEquals(
            Company.query.all()[-1].contracts[0].id,
            contract.id
        )

        # assert that creating a company with an existing
        # contract by id should work
        company_with_contract_id_data = dict(
            company_name='company three',
            contracts=[contract.id]
        )
        create_new_company(company_with_contract_id_data)
        self.assertEquals(Company.query.count(), 3)

        # assert that nonexistant contracts can't be assigned
        # to a company
        company_with_bad_contract_data = dict(
            company_name='company four',
            contracts=[999]
        )
        self.assertRaises(
            Exception, create_new_company, company_with_bad_contract_data
        )
        self.assertEquals(Company.query.count(), 3)

        company_with_bad_contract_data_two = dict(
            company_name='company four',
            contracts=[None]
        )
        self.assertRaises(
            Exception, create_new_company, company_with_bad_contract_data_two
        )
        self.assertEquals(Company.query.count(), 3)

        # assert that you can't have duplicate names
        self.assertRaises(
            IntegrityError, create_new_company, company_data
        )

    def test_update_company(self):
        company = insert_a_company()
        self.assertEquals(
            Company.query.first().company_name,
            company.company_name
        )

        update_company(company.id, {'company_name': 'new company'})
        self.assertEquals(
            Company.query.first().company_name,
            'new company'
        )

    def test_delete_company(self):
        company = insert_a_company()
        self.assertEquals(Company.query.count(), 1)
        self.assertEquals(ContractBase.query.count(), 1)

        delete_company(company.id)
        self.assertEquals(Company.query.count(), 0)
        self.assertEquals(ContractBase.query.count(), 1)

    def test_get_all_companies(self):
        insert_a_company()
        insert_a_company(name='new company 2')
        insert_a_company(name='new company 3')

        self.assertEquals(len(get_all_companies()), 3)
