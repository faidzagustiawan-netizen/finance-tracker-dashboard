#!/usr/bin/env python3
"""
Tests for the finance tracker: amount parsing, trip tagging, and the reply
format. Runs against a throwaway database so it never touches finance.db.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/finance-tracker')

from finance_tracker import FinanceTracker
from command_handler import FinanceCommandHandler


class AmountParsingTest(unittest.TestCase):
    """The amount parser has to accept how people actually type rupiah."""

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        self.t = FinanceTracker(self.path)

    def tearDown(self):
        self.t.get_connection().close()
        os.unlink(self.path)

    def amount(self, text):
        parsed = self.t.parse_transaction_input(text)
        return parsed['amount'] if parsed else None

    def test_plain_integer(self):
        self.assertEqual(self.amount('makan 40000'), 40000)

    def test_dot_grouped(self):
        self.assertEqual(self.amount('makan 40.000'), 40000)

    def test_comma_grouped(self):
        self.assertEqual(self.amount('makan 40,000'), 40000)

    def test_rb_suffixes(self):
        for text in ('makan 40rb', 'makan 40 rb', 'makan 40ribu'):
            self.assertEqual(self.amount(text), 40000, text)

    def test_k_suffix(self):
        self.assertEqual(self.amount('makan 40k'), 40000)

    def test_juta(self):
        self.assertEqual(self.amount('sewa 2jt'), 2000000)
        self.assertEqual(self.amount('sewa 2 juta'), 2000000)

    def test_decimal_juta(self):
        self.assertEqual(self.amount('sewa 1.5jt'), 1500000)
        self.assertEqual(self.amount('sewa 1,5jt'), 1500000)

    def test_rp_prefix(self):
        self.assertEqual(self.amount('makan Rp40.000'), 40000)
        self.assertEqual(self.amount('makan rp 40.000'), 40000)

    def test_large_grouped(self):
        self.assertEqual(self.amount('beli laptop 12.500.000'), 12500000)

    def test_ignores_small_bare_numbers(self):
        """'2 hari' must not be mistaken for the amount when 40rb is present."""
        self.assertEqual(self.amount('makan 2 hari 40rb'), 40000)

    def test_no_amount_returns_none(self):
        self.assertIsNone(self.amount('makan siang enak'))

    def test_description_excludes_amount(self):
        parsed = self.t.parse_transaction_input(
            'makan siang gulai depan stasiun pasarturi 40.000')
        self.assertEqual(parsed['description'],
                         'makan siang gulai depan stasiun pasarturi')


class TripTest(unittest.TestCase):

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        self.t = FinanceTracker(self.path)
        self.h = FinanceCommandHandler(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_create_and_find(self):
        trip_id = self.t.create_trip('Padang', end_date='2026-10-04')
        self.assertIsNotNone(trip_id)
        self.assertEqual(self.t.get_trip('padang')['id'], trip_id)
        self.assertEqual(self.t.get_trip('Padang')['id'], trip_id)
        self.assertEqual(self.t.get_trip('padang')['name'], 'Padang')

    def test_duplicate_slug_rejected(self):
        self.assertIsNotNone(self.t.create_trip('Padang'))
        self.assertIsNone(self.t.create_trip('padang'))

    def test_active_trip_respects_window(self):
        self.t.create_trip('Padang', start_date='2026-09-18',
                           end_date='2026-10-04')
        self.assertIsNotNone(self.t.get_active_trip())

    def test_expired_trip_not_active(self):
        self.t.create_trip('Lama', start_date='2026-01-01',
                           end_date='2026-01-10')
        self.assertIsNone(self.t.get_active_trip())

    def test_future_trip_not_active(self):
        self.t.create_trip('Nanti', start_date='2027-01-01')
        self.assertIsNone(self.t.get_active_trip())

    def test_end_trip(self):
        self.t.create_trip('Padang')
        self.assertTrue(self.t.end_trip('padang'))
        self.assertIsNone(self.t.get_active_trip())
        self.assertEqual(self.t.get_trip('padang')['status'], 'done')

    def test_expense_auto_tagged_to_active_trip(self):
        self.t.create_trip('Padang', end_date='2026-10-04')
        self.h.handle_message('makan 40.000')
        trip = self.t.get_active_trip()
        summary = self.t.get_trip_summary(trip['id'])
        self.assertEqual(summary['total'], 40000)
        self.assertEqual(summary['expense_count'], 1)

    def test_expense_not_tagged_without_trip(self):
        self.h.handle_message('makan 40.000')
        conn = self.t.get_connection()
        row = conn.execute(
            "SELECT trip_id FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNone(row['trip_id'])

    def test_summary_math(self):
        trip_id = self.t.create_trip('Padang', end_date='2026-10-04')
        self.t.add_expense(40000, 'Makanan', 'siang', trip_id=trip_id)
        self.t.add_expense(25000, 'Makanan', 'malam', trip_id=trip_id)
        self.t.add_expense(30000, 'Transport', 'ojek', trip_id=trip_id)
        s = self.t.get_trip_summary(trip_id)
        self.assertEqual(s['total'], 95000)
        self.assertEqual(s['expense_count'], 3)
        by_cat = {c['name']: c['total'] for c in s['by_category']}
        self.assertEqual(by_cat['Makanan'], 65000)
        self.assertEqual(by_cat['Transport'], 30000)

    def test_trip_commands(self):
        self.assertIn('Tidak ada trip aktif',
                      self.h.handle_message('/trip'))
        self.assertIn('Padang', self.h.handle_message('/trip mulai Padang'))
        self.assertIn('PADANG', self.h.handle_message('/trip'))
        self.h.handle_message('makan 40.000')
        self.assertIn('40,000', self.h.handle_message('/trip'))
        self.assertIn('Padang', self.h.handle_message('/trip list'))
        self.assertIn('ditutup', self.h.handle_message('/trip selesai'))


class ReplyFormatTest(unittest.TestCase):
    """
    The user asked for a short confirmation and the balance -- explicitly not a
    dump of past transactions.
    """

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        self.t = FinanceTracker(self.path)
        self.h = FinanceCommandHandler(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_reply_is_short_and_has_balance(self):
        reply = self.h.handle_message('makan siang gulai 40.000')
        self.assertIsInstance(reply, str)
        lines = reply.split('\n')
        self.assertLessEqual(len(lines), 4)
        self.assertIn('40,000', reply)
        self.assertIn('Saldo', reply)

    def test_reply_not_a_transaction_list(self):
        self.h.handle_message('makan 40.000')
        reply = self.h.handle_message('makan 25.000')
        # Only the new amount appears; the previous one is not re-listed.
        self.assertNotIn('40,000', reply)

    def test_reply_shows_trip_total_during_trip(self):
        self.h.handle_message('/trip mulai Padang')
        reply = self.h.handle_message('makan 40.000')
        self.assertIn('Padang', reply)


class AccountTest(unittest.TestCase):

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        self.t = FinanceTracker(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_no_dangling_account(self):
        """account_id must always point at a real account."""
        self.t.add_expense(40000, 'Makanan', 'test')
        conn = self.t.get_connection()
        dangling = conn.execute(
            "SELECT COUNT(*) FROM transactions "
            "WHERE account_id NOT IN (SELECT id FROM accounts)"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(dangling, 0)

    def test_explicit_account_respected(self):
        conn = self.t.get_connection()
        gopay = conn.execute(
            "SELECT id FROM accounts WHERE name = 'GoPay'").fetchone()['id']
        conn.close()
        self.t.add_expense(25000, 'Transport', 'ojek', account_id=gopay)
        conn = self.t.get_connection()
        row = conn.execute(
            "SELECT account_id FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertEqual(row['account_id'], gopay)

    def test_unknown_account_falls_back(self):
        self.t.add_expense(25000, 'Transport', 'ojek', account_id=9999)
        conn = self.t.get_connection()
        row = conn.execute(
            "SELECT account_id FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIn(row['account_id'],
                      [r['id'] for r in self.t.get_accounts()])


if __name__ == '__main__':
    unittest.main(verbosity=2)
