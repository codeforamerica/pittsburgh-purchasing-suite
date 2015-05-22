# -*- coding: utf-8 -*-

from flask import current_app
from collections import defaultdict

from purchasing.data.importer.costars import main
from purchasing.data.contracts import get_all_contracts
from purchasing.data.companies import get_all_companies
from purchasing.data.models import LineItem

from purchasing_test.unit.test_base import BaseTestCase

class TestCostarsImport(BaseTestCase):
    def test_costars_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/COSTARS-1.csv', 'COSTARS-1.csv', None, None, None)

        contracts = get_all_contracts()
        # assert we got both contracts
        self.assertEquals(len(contracts), 2)

        # assert that we got all the line items
        self.assertEquals(LineItem.query.count(), 12)

        props = defaultdict(list)

        companies = get_all_companies()
        self.assertEquals(len(companies), 2)
        for company in companies:
            self.assertEquals(company.contacts.count(), 0)

        for contract in contracts:
            self.assertTrue(contract.expiration_date is not None)
            for property in contract.properties:
                props[property.key].append(property.value)

        # assert the county importer works properly
        self.assertEquals(len(props['Located in']), 1)
        self.assertEquals(len(props['List of manufacturers']), 2)
