# -*- coding: utf-8 -*-

from flask import current_app

from purchasing.data.importer.old_contracts import main
from purchasing.data.contracts import get_all_contracts
from purchasing.data.companies import get_all_companies

from purchasing_test.unit.test_base import BaseTestCase

class TestOldContractsImport(BaseTestCase):
    def test_old_contracts_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/old_contracts.csv')

        # assert we get all contracts and companies
        contracts = get_all_contracts()
        self.assertEquals(len(contracts), 3)

        companies = get_all_companies()
        self.assertEquals(len(companies), 3)

        controller_nums = [45753, 50582, 47894]

        for contract in contracts:
            self.assertTrue(contract.financial_id in controller_nums)
            controller_nums.remove(contract.financial_id)

        self.assertEquals(len(controller_nums), 0)
