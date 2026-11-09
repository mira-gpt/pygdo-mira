import unittest
from decimal import Decimal

from gdo.mira.BtxPricing import btx_price


class BtxPricingTest(unittest.TestCase):
    def test_rounds_total_up_not_each_character(self):
        self.assertEqual(1, btx_price('123456789012345', Decimal('0.05')))
        self.assertEqual(15, btx_price('123456789012345', Decimal('1.00')))
        self.assertEqual(2, btx_price('abc', Decimal('0.50')))

    def test_counts_spaces_and_unicode_code_points(self):
        self.assertEqual(3, btx_price('a ä', '1.00'))

    def test_rejects_invalid_values(self):
        for text, rate in [('', '1'), ('  ', '1'), ('x', '-1'), ('x', 'NaN'), ('x', '0.001')]:
            with self.subTest(text=text, rate=rate), self.assertRaises(ValueError):
                btx_price(text, rate)
