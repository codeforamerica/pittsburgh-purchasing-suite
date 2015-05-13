# -*- coding: utf-8 -*-

import urllib
import datetime
import re

import scrapelib
from bs4 import BeautifulSoup
from urlparse import urlparse

from purchasing.database import db
from purchasing.data.contracts import get_all_contracts
from purchasing.data.models import ContractBase

BASE_COUNTY_URL = 'http://www.govbids.com/scripts/PAPG/public/OpenBids/ViewSolicitations.asp?' + \
    'page=1&Agency=1100&AgencyName=Allegheny+County+-+Division+of+Purchasing+and+Supplies&DisplayBy=' + \
    '&Year=&TitleSearch=&SortBy=&SortOrder=&ShowAll=Y'

BASE_LINE_ITEM_URL = 'http://www.govbids.com/scripts/PAPG/public/OpenBids/NoticeAward.asp?' + \
    'BN={document_number}&TN={tn}&' + \
    'AN=Allegheny%20County%20-%20Division%20of%20Purchasing%20and%20Supplies&AID=1100'

ITEM_NUMBER_REGEX = re.compile('Item #\d')

def not_main_window(driver, main_window):
    final_window = None
    for window in driver.window_handles:
        if window == main_window:
            pass
    else:
        final_window = window

    return final_window

def grab_line_items(soup):
    '''
    Goes through a page of awards, grabbing the individual
    line items
    '''
    line_items = []
    award_form = soup.find('form')

    if award_form is None:
        return None

    # note - the <form> tag is malformed and closes early,
    # so we can't use tables that are child nodes of the form --
    # we have to grab all tables
    tables = soup.find_all('table')

    # indices 0 - 5 are all metadata tables
    # index -1 is also a "metadata table" (the close window button)
    tables = tables[5:-1]

    for table in tables:
        if table.find(text=ITEM_NUMBER_REGEX):
            description = table.find_all('td')[1].contents[0]

        else:
            # award table -- occasionally these will have tbody nodes.
            # sometimes they don't. this is important because there are
            # sometimes nested tables, so we can't recursively grab all
            # tr elements.
            suppliers_table = table.find('tbody') if table.find('tbody') else table

            for supplier in suppliers_table.find_all('tr', recursive=False):

                # for some reason, they don't use actual radio boxes but
                # instead of _images_ of radio boxes. so look for those.
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
                    # ocassionally, there aren't manufacturers.
                    try:
                        manufacturer = manufacturer_fields[2].text.strip()
                        model_number = manufacturer_fields[4].text.strip()
                    except IndexError:
                        manufacturer, model_number = None, None

                # if we don't find either the image, or the proper image, continue
                else:
                    continue

                line_items.append({
                    'description': description, 'quantity': quantity,
                    'unit_of_measure': unit_of_measure,
                    'unit_cost': unit_cost, 'total_cost': total_cost,
                    'manufacturer': manufacturer, 'model_number': model_number
                })

    return line_items

def build_alert_links(link, document_number):
    '''
    Builds a link to the award determination site.

    Takes in a link td and a document number (already parsd). Returns
    a formatted LINE_ITEM_URL
    '''
    url = link.find('a')['href']
    url_params = dict([(i.split('=')) for i in urlparse(url).query.split('&')])
    TN = url_params['TN']

    return BASE_LINE_ITEM_URL.format(
        tn=TN,
        document_number=document_number
    )

def generate_line_item_links(item_table):
    '''
    Crawls through a table of information and pulls out
    related IFB information.

    Returns a list of 3-tuples that contain:
        + the link
        + the stripped IFB number
        + the deadline that that contract was due
    '''
    line_item_links = []

    for tr in item_table.find_all('tr', recursive=False):
        # make sure that we have three columns
        if len(tr.find_all('td')) != 3:
            continue

        # skip any table headings
        if len(tr.find_all('td', class_='tableheadings')) > 0:
            continue

        link, document_td, deadline = tr.find_all('td')

        document_number = urllib.quote(document_td.text.strip())
        if not document_number.startswith('IFB'):
            continue

        line_item_links.append((
            build_alert_links(link, document_number),
            document_number,
            datetime.datetime.strptime(deadline.text.strip(), '%m/%d/%Y')
        ))

    return line_item_links

def main():
    '''
    Boots up and starts the scraping
    '''
    s = scrapelib.Scraper(requests_per_minute=120, retry_attempts=2, retry_wait_seconds=2)
    skipped = 0
    line_items = []

    main_page = BeautifulSoup(s.get(BASE_COUNTY_URL).text)

    item_table = main_page.find('table', recursive=False)
    line_item_links = generate_line_item_links(item_table)

    for ix, (line_item_link, ifb, deadline) in enumerate(line_item_links):
        try:
            if ix % 50 == 0:
                print 'scraped {n} records'.format(n=ix)
            line_item_page = BeautifulSoup(s.get(line_item_link).text)
            _line_items = grab_line_items(line_item_page)
            if _line_items:
                line_items.append((_line_items, ifb, deadline))
            else:
                skipped += 1
        except scrapelib.HTTPException:
            print 'Could not open {url}, skipping'.format(url=line_item_link)
            continue

    print 'Completed! Parsed {ix} records, ({skipped} skipped)'.format(
        ix=len(line_items), skipped=skipped
    )
