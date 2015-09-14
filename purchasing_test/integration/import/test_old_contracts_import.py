# -*- coding: utf-8 -*-

from flask import current_app

from purchasing.data.importer.old_contracts import main
from purchasing.data.contracts import ContractBase
from purchasing.data.companies import Company

from purchasing_test.test_base import BaseTestCase

class TestOldContractsImport(BaseTestCase):
    def test_old_contracts_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/old_contracts.csv')

        # assert we get all contracts and companies
        contracts = ContractBase.query.all()
        self.assertEquals(len(contracts), 3)

        companies = Company.query.all()
        self.assertEquals(len(companies), 3)

        controller_nums = ['49020', '49011', '49189']

        for contract in contracts:
            self.assertTrue(contract.financial_id in controller_nums)
            controller_nums.remove(contract.financial_id)

        self.assertEquals(len(controller_nums), 0)
