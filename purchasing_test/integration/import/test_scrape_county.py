# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup

from flask import current_app

from purchasing.data.importer.scrape_county import (
    generate_line_item_links,
    grab_line_items, get_contract, save_line_item
)

from purchasing.opportunities import models
from purchasing.users.models import User
from purchasing.data.contracts import ContractBase, LineItem, ContractProperty
from purchasing.data.companies import Company

from purchasing_test.test_base import BaseTestCase

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
        muni = Company.create(**dict(company_name='U.S. Municipal Supply, Inc.'))
        chemung = Company.create(**dict(company_name='Chemung Supply Corporation'))
        pathmaster = Company.create(**dict(company_name='Path Master, Inc., Co.'))

        new_contract = ContractBase.create(
            **dict(properties=[ContractProperty(key='foo', value='6965')], description='foo')
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
            if 'muni' in item.company_name.lower():
                self.assertEquals(item.company_id, muni.id)
            elif 'chem' in item.company_name.lower():
                self.assertEquals(item.company_id, chemung.id)
            else:
                self.assertEquals(item.company_id, pathmaster.id)
