# -*- coding: utf-8 -*-

import datetime
from unittest import TestCase
from purchasing.filters import (
    better_title, format_currency, days_from_today,
    datetimeformat
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

    def test_days_from_today(self):
        '''Test days from today filter
        '''
        self.assertEquals(days_from_today(datetime.date.today()), 0)
        self.assertEquals(days_from_today(datetime.date.today() + datetime.timedelta(1)), 1)
        self.assertEquals(days_from_today(datetime.date.today() + datetime.timedelta(2)), 2)
        self.assertEquals(days_from_today(datetime.date.today() - datetime.timedelta(2)), -2)
        self.assertEquals(days_from_today(datetime.datetime.today() + datetime.timedelta(2)), 2)

    def test_datetimeformat(self):
        '''Test datetime format filter
        '''
        self.assertEquals(datetimeformat('2015-01-01T00:00:00'), '2015-01-01')
        self.assertEquals(datetimeformat('2015-01-01T00:00:00', '%B %d, %Y'), 'January 01, 2015')
        self.assertEquals(datetimeformat(datetime.date(2015, 1, 1)), '2015-01-01')
