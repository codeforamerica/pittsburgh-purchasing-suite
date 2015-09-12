# -*- coding: utf-8 -*-

from flask import current_app
from collections import defaultdict

from purchasing.data.importer.costars import main
from purchasing.data.contracts import ContractBase, LineItem
from purchasing.data.companies import Company

from purchasing_test.unit.test_base import BaseTestCase

class TestCostarsImport(BaseTestCase):
    def test_costars_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/COSTARS-1.csv', 'COSTARS-1.csv', None, None, None)

        contracts = ContractBase.query.all()
        # assert we got both contracts
        self.assertEquals(len(contracts), 3)

        # assert that we got all the line items
        self.assertEquals(LineItem.query.count(), 12)

        props = defaultdict(list)

        companies = Company.query.all()
        self.assertEquals(len(companies), 3)
        for company in companies:
            self.assertEquals(company.contacts.count(), 0)

        for contract in contracts:
            self.assertTrue(contract.expiration_date is not None)
            for property in contract.properties:
                props[property.key].append(property.value)

        # assert the county importer works properly
        self.assertEquals(len(props['Located in']), 2)
        self.assertEquals(len(props['List of manufacturers']), 2)

    def test_raises_bad_filename(self):
        with self.assertRaises(IOError):
            main('', 'BADFILENAME', None, None, None)
