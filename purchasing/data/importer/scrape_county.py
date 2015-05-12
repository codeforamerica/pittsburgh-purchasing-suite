# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from purchasing.database import db
from purchasing.data.contracts import get_all_contracts
from purchasing.data.models import ContractBase

driver = webdriver.Firefox()
BASE_COUNTY_URL = 'http://www.govbids.com/scripts/PAPG/public/OpenBids/ViewSolicitations.asp?' + \
    'page=1&Agency=1100&AgencyName=Allegheny+County+-+Division+of+Purchasing+and+Supplies&DisplayBy=' + \
    '&Year=&TitleSearch=&SortBy=&SortOrder=&ShowAll=Y'

def not_main_window(driver, main_window):
    final_window = None
    for window in driver.window_handles:
        if window == main_window:
            pass
    else:
        final_window = window

    return final_window

def main():
    try:
        line_items = {}

        driver.get(BASE_COUNTY_URL)

        main_window = driver.current_window_handle

        # create a list of all TRs in the proper dropdown
        contracts = driver.find_elements(By.XPATH, "//tr[@bgcolor='#FFFFFF']")

        for i in xrange(len(contracts)):
            contracts = driver.find_elements(By.XPATH, "//tr[@bgcolor='#FFFFFF']")
            contract = contracts[i]

            contract_props = contract.find_elements(By.TAG_NAME, 'td')

            if len(contract_props) != 3:
                continue

            full_spec = contract_props[1].text.split('-')

            if full_spec[0] != 'IFB' or len(full_spec) != 2:
                continue

            line_items[full_spec[1]] = []

            driver.find_element_by_xpath(
                "//td[contains(text(), '{spec}')]".format(spec=contract_props[1].text)
            ).find_element_by_xpath('..').find_element_by_tag_name('a').click()

            try:
                driver.find_element_by_css_selector(
                    '.subtitle'
                ).find_element_by_xpath('..').find_element_by_tag_name('a').click()
            except NoSuchElementException, e:
                # there was no award for this bid. skip it.
                driver.get(BASE_COUNTY_URL)
                continue

            driver.switch_to_window(not_main_window(driver, main_window))

            soup = BeautifulSoup(driver.page_source)
            tables = soup.find_all('table')

            for table in enumerate(tables[2:]):
                if len(table.find_all('tr')) == 1:
                    # item table
                    try:
                        description = table.find_all('td')[1].text

                    except IndexError:
                        pass

                elif len(table.find_all('tr')[0].find_all('td')) == 6:
                    # award table

                    suppliers_table = table.find('tbody') if table.find('tbody') else table

                    for supplier in suppliers_table.find_all('tr', recursive=False):

                        if supplier.find('td').find('img') and supplier.find('td').find('img').get('src') == '/images/system/RadioChkd-blgr.gif':

                            if len(supplier.find_all('td')) <= 2:
                                continue

                            fields = supplier.find_all('td', recursive=False)

                            if len(fields) < 6:
                                continue

                            quantity = fields[2].text.strip()
                            unit_of_measure = fields[3].text.strip()
                            unit_cost = fields[4].text.strip()
                            total_cost = fields[5].text.strip()

                            manufacturer_fields = fields[1].find_all('td')
                            try:
                                manufacturer = manufacturer_fields[2].text.strip()
                                model_number = manufacturer_fields[4].text.strip()
                            except IndexError:
                                manufacturer, model_number = None, None

                        else:
                            continue

                        line_items[full_spec[1]].append({
                            'description': description, 'quantity': quantity,
                            'unit_of_measure': unit_of_measure,
                            'unit_cost': unit_cost, 'total_cost': total_cost,
                            'manufacturer': manufacturer, 'model_number': model_number
                        })
                else:
                    continue

            driver.switch_to_window(main_window)
            driver.get(BASE_COUNTY_URL)

        print line_items

    except Exception, e:
        print line_items
        raise e

    finally:
        for window in driver.window_handles:
            driver.switch_to_window(window)
            driver.close()
