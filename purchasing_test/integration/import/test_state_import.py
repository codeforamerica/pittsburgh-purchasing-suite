# -*- coding: utf-8 -*-

from flask import current_app

from purchasing.data.importer.state import main
from purchasing.data.contracts import ContractBase
from purchasing.data.companies import Company, CompanyContact

from purchasing_test.test_base import BaseTestCase

class TestStateContractsImport(BaseTestCase):
    def test_state_contracts_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/state.csv')

        # assert we get all contracts and companies
        contracts = ContractBase.query.all()
        self.assertEquals(len(contracts), 2)

        companies = Company.query.all()
        self.assertEquals(len(companies), 2)

        contacts = CompanyContact.query.all()
        self.assertEquals(len(contacts), 1)

        contract_nums = ['4400004760', '4400006326']

        for contract in contracts:
            contract_properties = contract.properties
            self.assertTrue('Parent Number' in [i.key for i in contract_properties])
            self.assertTrue('Contract Number' in [i.key for i in contract_properties])

            contract_number = [i.value for i in contract_properties if i.key == 'Contract Number'][0]
            self.assertTrue(contract_number in contract_nums)
            contract_nums.remove(contract_number)
