#!/usr/bin/env python3
"""
Tests for the trip companion bot.

The point of this module is that it is NARROW: companions on a trip can log
expenses into that trip and read its total, and nothing else. Most of these
tests exist to pin that boundary down, because a regression here would hand a
third party access to the owner's salary, debts, or other accounts.
"""

import os
import tempfile
import unittest

from trip_bot import TripWhatsAppBot, normalise_phone, load_trip_users

FAIDZ = '62895397133738'
FIKRI = '6281228507417'
NABIL = '6282286361965'
STRANGER = '6280000000000'


class TripBotTest(unittest.TestCase):

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        # The bot's allowlist is fixed for the test so it does not depend on
        # whoever happens to be configured on the machine.
        self.users = {FAIDZ: 'Faidz', FIKRI: 'Fikri', NABIL: 'Nabil'}
        self.bot = TripWhatsAppBot(self.path, trip_ref='padang', users=self.users)
        self.trip_id = self.bot.tracker.create_trip(
            'Padang (Final Lomba)', end_date='2026-10-04')

    def tearDown(self):
        os.unlink(self.path)

    # ─────────────── access control ───────────────

    def test_allowed_numbers_recognised(self):
        self.assertTrue(self.bot.is_allowed(FIKRI))
        self.assertTrue(self.bot.is_allowed(NABIL))

    def test_number_with_punctuation_still_matches(self):
        # WhatsApp identifiers arrive as "+62 812-2850-7417" or
        # "6281228507417@s.whatsapp.net"; both must resolve to the same person.
        self.assertTrue(self.bot.is_allowed('+62 812-2850-7417'))
        self.assertTrue(self.bot.is_allowed('6281228507417@s.whatsapp.net'))

    def test_stranger_gets_no_reply(self):
        # Silence, rather than "not authorised": an unknown number should not
        # even learn that this bot exists.
        self.assertEqual(self.bot.handle(STRANGER, 'makan 10rb'), '')

    def test_stranger_cannot_write(self):
        self.bot.handle(STRANGER, 'makan 10rb')
        summary = self.bot.tracker.get_trip_summary(self.trip_id)
        self.assertEqual(summary['expense_count'], 0)

    # ─────────────── recording ───────────────

    def test_records_expense_into_trip(self):
        reply = self.bot.handle(FIKRI, 'makan malam 45.000')
        self.assertIn('45,000', reply)
        summary = self.bot.tracker.get_trip_summary(self.trip_id)
        self.assertEqual(summary['total'], 45000)
        self.assertEqual(summary['expense_count'], 1)

    def test_expense_is_tagged_with_payer(self):
        # The payer is what the group settles up on later, so it must survive.
        self.bot.handle(FIKRI, 'makan malam 45.000')
        summary = self.bot.tracker.get_trip_summary(self.trip_id)
        self.assertIn('[Fikri]', summary['items'][0]['description'])

    def test_accepts_indonesian_amount_formats(self):
        for text, expected in [('makan 45.000', 45000),
                               ('makan 45rb', 45000),
                               ('makan 45000', 45000),
                               ('makan Rp45.000', 45000)]:
            with self.subTest(text=text):
                fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
                try:
                    bot = TripWhatsAppBot(path, trip_ref='padang',
                                          users=self.users)
                    trip = bot.tracker.create_trip('Padang Trip')
                    reply = bot.handle(FIKRI, text)
                    self.assertIn(f'{expected:,}', reply)
                    self.assertEqual(
                        bot.tracker.get_trip_summary(trip)['total'], expected)
                finally:
                    os.unlink(path)

    def test_both_companions_log_to_same_trip(self):
        self.bot.handle(FIKRI, 'makan 45.000')
        self.bot.handle(NABIL, 'grab 31.000')
        summary = self.bot.tracker.get_trip_summary(self.trip_id)
        self.assertEqual(summary['total'], 76000)
        self.assertEqual(summary['expense_count'], 2)

    def test_unparseable_input_asks_for_amount(self):
        reply = self.bot.handle(FIKRI, 'makan enak')
        self.assertIn('nominal', reply.lower())
        self.assertEqual(
            self.bot.tracker.get_trip_summary(self.trip_id)['expense_count'], 0)

    # ─────────────── the boundary ───────────────

    def test_income_refused(self):
        for text in ('gajian 5jt', 'bonus 1jt', 'terima transfer 500rb'):
            with self.subTest(text=text):
                reply = self.bot.handle(FIKRI, text)
                self.assertIn('pengeluaran', reply.lower())

    def test_income_never_written(self):
        self.bot.handle(FIKRI, 'gajian 5jt')
        balance = self.bot.tracker.get_balance()
        self.assertEqual(balance['income'], 0)

    def test_debt_refused(self):
        reply = self.bot.handle(FIKRI, 'hutang fikri 50rb')
        self.assertIn('/help', reply)

    def test_delete_refused(self):
        self.bot.handle(FIKRI, 'makan 45.000')
        reply = self.bot.handle(FIKRI, 'hapus semua data')
        self.assertIn('/help', reply)
        # The earlier expense must still be there.
        self.assertEqual(
            self.bot.tracker.get_trip_summary(self.trip_id)['expense_count'], 1)

    def test_cannot_create_another_trip(self):
        self.bot.handle(FIKRI, 'trip mulai Bali 5jt')
        trips = self.bot.tracker.get_connection().execute(
            "SELECT COUNT(*) FROM trips").fetchone()[0]
        self.assertEqual(trips, 1)

    def test_cannot_read_other_balances(self):
        # /balance is the owner's salary-and-debts view and must not be reachable.
        reply = self.bot.handle(FIKRI, '/balance')
        self.assertNotIn('Saldo', reply)

    # ─────────────── reading ───────────────

    def test_trip_summary_shows_total(self):
        self.bot.handle(FIKRI, 'makan 45.000')
        reply = self.bot.handle(NABIL, '/trip')
        self.assertIn('45,000', reply)
        self.assertIn('PADANG', reply.upper())

    def test_summary_categories_listed(self):
        self.bot.handle(FIKRI, 'makan 45.000')
        self.bot.handle(NABIL, 'grab ke terminal 31.000')
        reply = self.bot.handle(FIKRI, '/trip')
        self.assertIn('Makanan', reply)
        self.assertIn('Transport', reply)

    def test_help_lists_only_supported_actions(self):
        reply = self.bot.handle(FIKRI, '/help')
        self.assertIn('/trip', reply)
        self.assertNotIn('/balance', reply)

    # ─────────────── trip resolution ───────────────

    def test_partial_trip_name_resolves(self):
        # "padang" must find "padang-final-lomba"; a naive exact-slug lookup
        # would silently refuse every expense.
        self.bot.handle(FIKRI, 'makan 45.000')
        self.assertEqual(
            self.bot.tracker.get_trip_summary(self.trip_id)['expense_count'], 1)

    def test_falls_back_to_active_trip(self):
        bot = TripWhatsAppBot(self.path, trip_ref='trip-yang-tidak-ada',
                              users=self.users)
        reply = bot.handle(FIKRI, 'makan 45.000')
        self.assertIn('45,000', reply)

    def test_no_trip_gives_clear_message(self):
        fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
        try:
            bot = TripWhatsAppBot(path, trip_ref='padang', users=self.users)
            reply = bot.handle(FIKRI, 'makan 45.000')
            self.assertIn('Trip', reply)
        finally:
            os.unlink(path)


class HelperTest(unittest.TestCase):

    def test_normalise_phone(self):
        for raw in ('+62 812-2850-7417', '6281228507417@s.whatsapp.net',
                    '6281228507417:12@s.whatsapp.net', '6281228507417'):
            with self.subTest(raw=raw):
                self.assertEqual(normalise_phone(raw), '6281228507417')

    def test_load_users_from_file(self):
        fd, path = tempfile.mkstemp(suffix='.json'); os.close(fd)
        try:
            with open(path, 'w') as fh:
                fh.write('{"6281228507417": {"name": "Fikri"}}')
            users = load_trip_users(path)
            self.assertEqual(users.get('6281228507417'), 'Fikri')
        finally:
            os.unlink(path)

    def test_malformed_file_does_not_crash(self):
        fd, path = tempfile.mkstemp(suffix='.json'); os.close(fd)
        try:
            with open(path, 'w') as fh:
                fh.write('{not json')
            self.assertEqual(load_trip_users(path), {})
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
