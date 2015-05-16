# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

from purchasing.data.importer.scrape_county import (
    generate_line_item_links,
    grab_line_items, get_contract, save_line_item,
    BASE_COUNTY_URL
)
from purchasing.data.contracts import create_new_contract
from purchasing.data.models import LineItem

from purchasing_test.unit.test_base import BaseTestCase

class TestScrapeCounty(BaseTestCase):
    def test_scrape_county(self):
        try:
            main_page = BeautifulSoup(
                requests.get(BASE_COUNTY_URL, timeout=3).content,
                from_encoding='windows-1252'
            )

            item_table = main_page.find('table', recursive=False)
            line_item_links = generate_line_item_links(item_table)

            self.assertEquals(len(line_item_links[0]), 4)
            # this had 640 as of 2015-05-14, so it should never
            # have less than 600 as they keep adding onto it
            self.assertTrue(len(line_item_links) > 600)

        # if the page load times out, don't fail the tests
        except requests.exceptions.Timeout:
            self.assertTrue(True)

        except Exception:
            raise

    def test_import_line_items(self):
        try:
            new_contract = create_new_contract(
                dict(properties=[dict(key='foo', value='7421')], description='foo')
            )
            line_item_link = 'http://www.govbids.com/scripts/PAPG/public/OpenBids/NoticeAward.asp?BN=IFB-7421&TN=104331&AN=Allegheny%20County%20-%20Division%20of%20Purchasing%20and%20Supplies&AID=1100'

            line_item_page = BeautifulSoup(
                requests.get(line_item_link, timeout=3).content,
                from_encoding='windows-1252'
            )

            _line_items = grab_line_items(line_item_page)
            self.assertEquals(len(_line_items), 43)

            contract = get_contract(
                'PAVERLAID HOT MIX PAVING, ETC. (CD AREAS INCLUDED) II',
                'IFB-7421'
            )
            self.assertTrue(contract is not None)
            self.assertEquals(contract.id, new_contract.id)

            save_line_item(_line_items, contract)

            self.assertEquals(LineItem.query.count(), len(_line_items))

        # if the page load times out, don't fail the tests
        except requests.exceptions.Timeout:
            self.assertTrue(True)

        except Exception:
            raise
