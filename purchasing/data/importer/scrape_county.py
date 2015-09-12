# -*- coding: utf-8 -*-

import urllib
import datetime
import re
from decimal import Decimal

import scrapelib
from bs4 import BeautifulSoup
from urlparse import urlparse

from sqlalchemy import or_
from purchasing.database import db
from purchasing.data.contracts import ContractBase, ContractProperty, LineItem
from purchasing.public.models import AppStatus

from purchasing.data.importer import get_or_create

BASE_COUNTY_URL = 'http://www.govbids.com/scripts/PAPG/public/OpenBids/ViewSolicitations.asp?' + \
    'page=1&Agency=1100&AgencyName=Allegheny+County+-+Division+of+Purchasing+and+Supplies&DisplayBy=' + \
    '&Year=&TitleSearch=&SortBy=&SortOrder=&ShowAll=Y'

BASE_LINE_ITEM_URL = 'http://www.govbids.com/scripts/PAPG/public/OpenBids/NoticeAward.asp?' + \
    'BN={document_number}&TN={tn}&' + \
    'AN=Allegheny%20County%20-%20Division%20of%20Purchasing%20and%20Supplies&AID=1100'

ITEM_NUMBER_REGEX = re.compile('Item #\d+')
CURRENCY_REGEX = re.compile('[^\d.]')
PERCENT_REGEX = re.compile('([Pp][Ee][Rr][Cc][Ee][Nn][Tt]).*')

def parse_item_table(item_table):
    item_description_contents = item_table.find_all('td')[1]
    manufacturer, model_number = None, None
    description = item_description_contents.contents[0]

    if 'Brand Name Only' in str(item_description_contents):
            contents = str(item_description_contents).split('<br>')
            try:
                manufacturer = BeautifulSoup(contents[2]).text.split()[1]
                model_number = BeautifulSoup(contents[3]).text.split()[1]
            except IndexError:
                pass

    return description, manufacturer, model_number

def parse_award_table(award_table):
    # award table -- occasionally these will have tbody nodes.
    # sometimes they don't. this is important because there are
    # sometimes nested tables, so we can't recursively grab all
    # tr elements.
    suppliers_table = award_table.find('tbody') if award_table.find('tbody') else award_table

    quantity = None
    for supplier in suppliers_table.find_all('tr', recursive=False):

        # for some reason, they don't use actual radio boxes but
        # instead of _images_ of radio boxes. so look for those.
        if supplier.find('td').find('img') and \
           supplier.find('td').find('img').get('src') == '/images/system/RadioChkd-blgr.gif':

            if len(supplier.find_all('td')) <= 2:
                include = False
                continue

            if supplier.find_all('td')[-1].string.lower() == 'no award':
                include = False
                continue

            fields = supplier.find_all('td', recursive=False)

            if len(fields) < 6:
                include = False
                continue

            quantity = fields[2].text.strip()
            unit_of_measure = fields[3].text.strip()
            unit_cost = fields[4].text.strip()
            total_cost = fields[5].text.strip()

            company = fields[1].contents[0].text

            manufacturer_table = fields[1].find('table')

            if manufacturer_table is None:
                manufacturer, model_number = None, None
            elif len(manufacturer_table.find_all('tr')) == 1:
                # this manufacturer we can take from the item table because
                # it is either a no bid, or it is using the quoting brand
                manufacturer, model_number = None, None
            else:
                # if we have more than this, we need to parse here for the
                # manufacturer.
                manufacturer = manufacturer_table.find_all('tr')[1].text.strip().split(':')[1]
                model_number = manufacturer_table.find_all('tr')[2].text.strip().split(':')[1]

            return quantity, unit_of_measure, unit_cost, total_cost, company, manufacturer, model_number

        # if we don't find either the image, or the proper image, continue
        else:
            continue

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
        # flag to skip this item due to it not having an awardee
        include = True
        # initialize all of our variables
        quantity = None
        manufacturer_lt, model_number_lt, manufacturer_at, model_number_at = None, None, None, None

        if table.find(text=ITEM_NUMBER_REGEX):
            # this is an item table, so use the item table parser
            description, manufacturer_lt, model_number_lt = parse_item_table(table)
        else:
            # award table -- occasionally these will have tbody nodes.
            # sometimes they don't. this is important because there are
            # sometimes nested tables, so we can't recursively grab all
            # tr elements.
            parsed_award_table = parse_award_table(table)

            if parsed_award_table:
                quantity, unit_of_measure, unit_cost, total_cost, \
                    company, manufacturer_at, model_number_at = parse_award_table(table)

        if description and quantity:
            manufacturer = manufacturer_lt or manufacturer_at
            model_number = model_number_lt or model_number_at

            line_items.append({
                'description': description, 'quantity': quantity,
                'unit_of_measure': unit_of_measure, 'company': company,
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

def generate_line_item_links(item_table, max_deadline=None):
    '''
    Crawls through a table of information and pulls out
    related IFB information. Skips rows that are older than
    the max_deadline

    Returns a list of 4-tuples that contain:
        + the link
        + the description from the site
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

        if len(document_number.split('-')) != 2:
            continue

        _deadline = datetime.datetime.strptime(deadline.text.strip(), '%m/%d/%Y')
        if max_deadline and _deadline <= max_deadline:
            continue

        line_item_links.append((
            build_alert_links(link, document_number),
            link.text.strip(),
            document_number,
            _deadline
        ))

    return line_item_links

def parse_currency(description, field):
    '''
    Takes descriptions, currency, returns currency, if percentage
    '''
    percent = re.search(PERCENT_REGEX, description)
    value = re.sub(CURRENCY_REGEX, '', field)

    if value == '':
        return None, False
    elif percent and float(value) < 1:
        return Decimal(value) * 100, True
    elif percent:
        return Decimal(value), True
    return Decimal(value), False

def get_contract(description, ifb):
    return db.session.query(
        ContractBase.id, ContractBase.description,
        ContractProperty.key, ContractProperty.value
    ).join(ContractProperty).filter(or_(
        ContractBase.description.ilike(description),
        ContractProperty.value.ilike(ifb.split('-')[1])
    )).first()

def save_line_item(_line_items, contract):
    '''
    Saves the line items to the db
    '''
    for item in _line_items:
        unit_cost, percentage = parse_currency(item.get('description'), item.get('unit_cost'))
        total_cost, _ = parse_currency(item.get('description'), item.get('total_cost'))

        linked_company = db.session.execute('''
        SELECT id, company_name
        FROM company
        WHERE company_name ilike '%' || :name || '%'
        OR (select count(*) from (
                select regexp_matches(lower(company_name), lower(:name))
        ) x ) > 0
        ''', {
            'name': item.get('company')
        }
        ).fetchone()

        company_id = linked_company[0] if linked_company else None

        line_item, new_line_item = get_or_create(
            db.session, LineItem,
            contract_id=contract.id,
            description=item.get('description'),
            manufacturer=item.get('manufacturer'),
            model_number=item.get('model_number'),
            quantity=item.get('quantity'),
            unit_of_measure=item.get('unit_of_measure'),
            unit_cost=unit_cost,
            total_cost=total_cost,
            percentage=percentage,
            company_name=item.get('company'),
            company_id=company_id
        )

        if new_line_item:
            db.session.add(line_item)

    db.session.commit()
    return

def main(_all=None):
    '''
    Boots up and starts the scraping.

    Takes an optional '_all' flag, which overrides
    the default date filtering and will try to pull down
    all records
    '''
    s = scrapelib.Scraper(requests_per_minute=120, retry_attempts=2, retry_wait_seconds=2)
    skipped, added = 0, 0
    max_date = datetime.datetime(1, 1, 1)
    status = AppStatus.query.first()

    main_page = BeautifulSoup(s.get(BASE_COUNTY_URL).content, from_encoding='windows-1252')

    item_table = main_page.find('table', recursive=False)

    if _all:
        line_item_links = generate_line_item_links(item_table)
    else:
        line_item_links = generate_line_item_links(item_table, status.county_max_deadline)

    print 'Scraping {} line item links'.format(len(line_item_links))

    for ix, (line_item_link, description, ifb, deadline) in enumerate(line_item_links):

        try:
            contract = get_contract(description, ifb)

            if ix % 50 == 0:
                print 'processed {n} records'.format(n=ix)

            if not contract:
                skipped += 1
                continue

            line_item_page = BeautifulSoup(s.get(line_item_link).content, from_encoding='windows-1252')
            _line_items = grab_line_items(line_item_page)

            if _line_items:

                if deadline > max_date:
                    max_date = deadline

                added += 1
                save_line_item(_line_items, contract)

            else:
                skipped += 1

            status.update(county_max_deadline=max_date)
            db.session.commit()

        except scrapelib.HTTPError:
            print 'Could not open {url}, skipping'.format(url=line_item_link)
            continue

        except Exception:
            raise

    print 'Completed! Parsed {ix} records, ({skipped} skipped)'.format(
        ix=added, skipped=skipped
    )
    return added, skipped
