# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

from flask import current_app

from purchasing.data.importer.scrape_county import (
    generate_line_item_links,
    grab_line_items, get_contract, save_line_item
)

from purchasing.data.contracts import create_new_contract
from purchasing.data.companies import create_new_company, get_all_companies
from purchasing.data.models import LineItem

from purchasing_test.unit.test_base import BaseTestCase

class TestScrapeCounty(BaseTestCase):
    def test_scrape_county(self):
        '''
        Test the building of new line item links.
        '''
        with open(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/all_bids.html', 'r') as f:
            main_page = BeautifulSoup(
                f.read(), from_encoding='windows-1252'
            )

        item_table = main_page.find('table', recursive=False)
        line_item_links = generate_line_item_links(item_table)

        self.assertEquals(len(line_item_links[0]), 4)

        # the single page we've CURLed down (2015-05-19) has 13 IFBs, so
        # there should be 13 line item links
        self.assertTrue(len(line_item_links) == 13)

    def test_import_line_items(self):
        '''
        Test that award information is scraped properly.
        '''
        create_new_company(dict(company_name='U.S. Municipal Supply, Inc.'))
        create_new_company(dict(company_name='Chemung Supply Corporation'))
        create_new_company(dict(company_name='Path Master, Inc.'))

        new_contract = create_new_contract(
            dict(properties=[dict(key='foo', value='6965')], description='foo')
        )

        with open(current_app.config.get('PROJECT_ROOT') + '/purchasing_test/mock/award.html', 'r') as f:
            line_item_page = BeautifulSoup(
                f.read(), from_encoding='windows-1252'
            )

        _line_items = grab_line_items(line_item_page)
        self.assertEquals(len(_line_items), 14)

        contract = get_contract(
            'Sign Post, Square Tubes, Brackets, Etc.',
            'IFB-6965'
        )
        self.assertTrue(contract is not None)
        self.assertEquals(contract.id, new_contract.id)

        save_line_item(_line_items, contract)

        self.assertEquals(LineItem.query.count(), len(_line_items))
        # assert that our ids made it in property
        for item in LineItem.query.all():
            self.assertTrue(item.manufacturer is not None)
            self.assertTrue(item.model_number is not None)
            self.assertEquals(item.contract_id, contract.id)
            self.assertTrue(item.company_id in [i.id for i in get_all_companies()])
