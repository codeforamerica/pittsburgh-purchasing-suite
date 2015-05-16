# -*- coding: utf-8 -*-

from flask import current_app
from collections import defaultdict

from purchasing.data.importer.costars import main
from purchasing.data.contracts import get_all_contracts
from purchasing.data.models import LineItem

from purchasing_test.unit.test_base import BaseTestCase

class TestCostarsImport(BaseTestCase):
    def test_costars_import(self):
        main(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/COSTARS_1.csv', 'COSTARS_1.csv')

        contracts = get_all_contracts()
        # assert we got both contracts
        self.assertEquals(len(contracts), 2)

        # assert that we got all the line items
        self.assertEquals(LineItem.query.count(), 4)

        props = defaultdict(list)

        for contract in contracts:
            for property in contract.properties:
                props[property.key].append(property.value)

        # assert the county importer works properly
        self.assertEquals(len(props['Located in']), 1)
        self.assertEquals(len(props['List of manufacturers']), 2)
