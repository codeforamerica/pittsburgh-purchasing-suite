# -*- coding: utf-8 -*-

import os
import datetime
import pytz

from unittest import TestCase
from flask import current_app
from flask_testing import TestCase as FlaskTestCase
from purchasing.app import create_app as _create_app
from purchasing.filters import (
    better_title, format_currency, days_from_today,
    datetimeformat, format_days_from_today, newline_to_br
)

class TestFilters(TestCase):
    def test_format_currency(self):
        '''Test currency format filter
        '''
        self.assertEquals(format_currency(1000), '$1,000.00')
        self.assertEquals(format_currency(10000000), '$10,000,000.00')
        self.assertEquals(format_currency(1.2345), '$1.23')
        self.assertEquals(format_currency(1.999999), '$2.00')

    def test_better_title(self):
        '''Test better title casing
        '''
        self.assertEquals(better_title('abcdef'), 'Abcdef')
        self.assertEquals(better_title('two words'), 'Two Words')
        self.assertEquals(better_title('THIS HAS A STOP WORD'), 'This Has a Stop Word')
        self.assertEquals(better_title('m.y. initials'), 'M.Y. Initials')
        self.assertEquals(
            better_title('the roman numeral string iii'),
            'The Roman Numeral String III'
        )
        self.assertEquals(better_title('costars pq llc'), 'COSTARS PQ LLC')
        self.assertEquals(better_title('I3456'), 'i3456')
        self.assertEquals(better_title('i3456'), 'i3456')

    def test_days_from_today(self):
        '''Test days from today filter
        '''
        self.assertEquals(days_from_today(datetime.date.today()), 0)
        self.assertEquals(days_from_today(datetime.date.today() + datetime.timedelta(1)), 1)
        self.assertEquals(days_from_today(datetime.date.today() + datetime.timedelta(2)), 2)
        self.assertEquals(days_from_today(datetime.date.today() - datetime.timedelta(2)), -2)
        self.assertEquals(days_from_today(datetime.datetime.today() + datetime.timedelta(2)), 2)

    def test_format_days_from_today(self):
        '''Test formatter for days from today
        '''
        self.assertEquals(format_days_from_today(datetime.date.today()), 'Today')
        self.assertEquals(format_days_from_today(datetime.date.today() + datetime.timedelta(1)), '1 day from now')
        self.assertEquals(format_days_from_today(datetime.date.today() - datetime.timedelta(1)), '1 day ago')
        self.assertEquals(format_days_from_today(datetime.date.today() + datetime.timedelta(2)), '2 days from now')
        self.assertEquals(format_days_from_today(datetime.date.today() - datetime.timedelta(2)), '2 days ago')


class TestDateTimeFormat(FlaskTestCase):
    def create_app(self):
        os.environ['CONFIG'] = 'purchasing.settings.TestConfig'
        return _create_app()

    def test_datetimeformat(self):
        '''Test datetime format filter
        '''
        self.assertEquals(datetimeformat('2015-01-01T00:00:00'), '2015-01-01')
        self.assertEquals(datetimeformat('2015-01-01T00:00:00', '%Y-%m-%d %I:%M%p', False), '2015-01-01 12:00AM')
        self.assertEquals(datetimeformat('2015-01-01T00:00:00', '%B %d, %Y'), 'January 01, 2015')
        self.assertEquals(datetimeformat(datetime.date(2015, 1, 1)), '2015-01-01')
        self.assertEquals(datetimeformat(None), '')

    def test_datetimefilter_timezone(self):
        '''Test datetime format filter with timezones
        '''
        current_app.config['DISPLAY_TIMEZONE'] = pytz.timezone('US/Eastern')
        self.assertEquals(datetimeformat('2015-01-01T00:00:01'), '2014-12-31')
        self.assertEquals(datetimeformat('2015-01-01T00:00:00'), '2015-01-01')
        self.assertEquals(datetimeformat(None), '')

    def test_newline_to_br(self):
        self.assertEquals(
            newline_to_br(None, 'test\r\n\r\ntest\r\n\r\ntest'),
            '<p>test</p>\n\n<p>test</p>\n\n<p>test</p>'
        )
        self.assertEquals(
            newline_to_br(None, 'test\ntest\r\n\r\ntest\r\n\r\ntest'),
            '<p>test<br>\ntest</p>\n\n<p>test</p>\n\n<p>test</p>'
        )

