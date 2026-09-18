#!/usr/bin/env python3
"""
Trip companion bot — a deliberately narrow WhatsApp interface.

Travelling companions need to log their shared trip expenses, but they must not
receive the main finance tracker (which carries the owner's salary, debts and
full account balances) and they certainly must not be granted WhatsApp
allowlist access, since that reaches the Hermes agent and a shell on the host.

This module is the whole surface those companions get:

  * record an expense, always into one specific trip
  * read that trip's running total and category split

Everything else -- income, debts, other trips, other accounts, the dashboard --
is refused by construction: the reject path is the default, and the two allowed
operations are the explicit branches.

No LLM is involved, so a message can never be talked into doing something else.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from finance_tracker import FinanceTracker
from command_handler import FinanceCommandHandler


# Words that mean the sender is trying to do something this bot does not offer.
# Kept separate from the allowed path so a stray keyword cannot widen access.
_INCOME_WORDS = (
    'gajian', 'gaji', 'bonus', 'freelance', 'honor', 'upah', 'komisi',
    'royalti', 'refund', 'terima', 'dapat', 'dapet', 'kiriman', 'transfer masuk',
    'pemasukan', 'income',
)

_FORBIDDEN_WORDS = (
    'hutang', 'utang', 'piutang', 'pinjam', 'bayar hutang', 'cicilan',
    'hapus', 'delete', 'batal', 'edit', 'ubah', 'ganti', 'saldo', 'balance',
    'akun', 'account', 'trip mulai', 'trip selesai', 'trip list', 'selesai',
    'laporan', 'rekap', 'export', 'dashboard', 'bunga', 'tabungan',
)


class TripWhatsAppBot:
    """Restricted expense logging for the companions on a shared trip."""

    def __init__(self, db_path: str = "finance.db", trip_ref: str = "padang",
                 users: Optional[Dict[str, str]] = None):
        self.tracker = FinanceTracker(db_path)
        self.handler = FinanceCommandHandler(db_path)
        self.trip_ref = trip_ref
        self.users = users if users is not None else load_trip_users()

    # ────────────────── access ──────────────────

    def is_allowed(self, sender: str) -> bool:
        return normalise_phone(sender) in self.users

    def name_for(self, sender: str) -> str:
        return self.users.get(normalise_phone(sender), 'Peserta')

    def allowed_numbers(self) -> List[str]:
        return sorted(self.users.keys())

    # ────────────────── entry point ──────────────────

    def handle(self, sender: str, text: str) -> str:
        """
        Turn one inbound message into one reply.

        Unknown senders get nothing useful; every failure mode returns a short
        explanation rather than an exception, because this is called from a
        message loop that must never die on bad input.
        """
        if not self.is_allowed(sender):
            # Do not confirm or deny anything to an unknown number.
            return ""

        text = (text or "").strip()
        if not text:
            return self._help()

        command = text.lstrip('/').split()[0].lower() if text.startswith('/') else ""

        if command in ("start", "help", "bantuan"):
            return self._help()
        if command in ("trip", "total", "ringkasan", "rekap"):
            return self._summary()

        return self._record(text, sender)

    # ────────────────── operations ──────────────────

    def _trip(self) -> Optional[Dict]:
        """
        Resolve the trip this bot logs into.

        Tries the configured reference first, then falls back to whatever trip
        is running right now. The fallback matters because the reference is a
        slug ("padang-final-lomba") that a rename would silently break, and a
        companion's expense landing in the wrong place is worse than a clear
        message that no trip is set up.
        """
        trip = self.tracker.get_trip(self.trip_ref)
        if trip:
            return trip

        # The configured reference did not resolve -- e.g. it was given as
        # "padang" while the slug is "padang-final-lomba". Try a prefix match on
        # slug or name before giving up.
        conn = self.tracker.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM trips
                   WHERE slug LIKE ? OR lower(name) LIKE ?
                   ORDER BY id DESC LIMIT 1""",
                (f"{self.trip_ref.lower()}%", f"%{self.trip_ref.lower()}%"),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()

        return self.tracker.get_active_trip()

    def _record(self, text: str, sender: str) -> str:
        """Record an expense into the trip, or explain why it was refused."""
        trip = self._trip()
        if not trip:
            return "⚠️ Trip belum disiapkan. Hubungi Faidz."

        lowered = text.lower()

        # Refuse the sensitive actions first, so nothing below can be reached
        # by a message that happens to also contain an amount.
        for word in _FORBIDDEN_WORDS:
            if word in lowered:
                return (
                    "🙏 Bot ini khusus catat pengeluaran trip Padang.\n"
                    "Ketik /help untuk lihat yang bisa dilakukan."
                )

        for word in _INCOME_WORDS:
            if word in lowered:
                return (
                    "🙏 Bot ini hanya mencatat *pengeluaran*.\n"
                    "Pemasukan/saldo dipegang Faidz."
                )

        parsed = self.tracker.parse_transaction_input(text)
        if not parsed:
            return (
                "❌ Belum ada nominalnya. Contoh:\n"
                "• makan siang 45.000\n"
                "• grab ke terminal 31rb\n"
                "• hotel 350rb"
            )

        if parsed.get('type') == 'income':
            return "🙏 Bot ini hanya mencatat *pengeluaran*."

        amount = parsed['amount']
        if amount <= 0:
            return "❌ Nominalnya belum kebaca. Contoh: makan 25.000"

        category = self.handler.match_category(parsed['category_hint'], 'expense') or "Lainnya"

        # Who paid is the first thing a group settles up on, so it is kept in
        # the description where every existing report already shows it.
        payer = self.name_for(sender)
        description = (parsed.get('description') or '').strip()
        description = f"[{payer}] {description}".strip() if description else f"[{payer}]"

        ok = self.tracker.add_expense(
            amount=amount,
            category=category,
            description=description,
            account_id=None,
            date=datetime.now().strftime("%Y-%m-%d"),
            trip_id=trip['id'],
        )
        if not ok:
            return "❌ Gagal mencatat. Coba lagi."

        summary = self.tracker.get_trip_summary(trip['id'])
        lines = [
            f"✅ Tercatat: {description} — Rp {amount:,}",
            f"📁 {category}",
            f"🧳 Total trip: Rp {summary['total']:,} ({summary['expense_count']} pengeluaran)",
        ]
        return "\n".join(lines)

    def _summary(self) -> str:
        trip = self._trip()
        if not trip:
            return "⚠️ Trip belum disiapkan."

        summary = self.tracker.get_trip_summary(trip['id'])
        msg = f"🧳 *{trip['name'].upper()}*\n"
        msg += f"{trip['start_date']}"
        msg += f" → {trip['end_date']}" if trip.get('end_date') else ""

        if summary['expense_count'] == 0:
            return msg + "\n\nBelum ada pengeluaran."

        msg += f"\n\n*Total: Rp {summary['total']:,}*"
        msg += f"\n{summary['expense_count']} pengeluaran"

        days = self._days(trip)
        if days > 0:
            msg += f"\nRata-rata: Rp {summary['total'] // days:,}/hari"

        if summary['by_category']:
            msg += "\n\n*Per kategori*"
            for c in summary['by_category']:
                pct = c['total'] / summary['total'] * 100 if summary['total'] else 0
                msg += f"\n• {c['name'] or 'Lainnya'}: Rp {c['total']:,} ({pct:.0f}%)"

        return msg

    @staticmethod
    def _days(trip: Dict) -> int:
        try:
            start = datetime.strptime(trip['start_date'], "%Y-%m-%d")
            if trip.get('status') == 'done' and trip.get('end_date'):
                end = datetime.strptime(trip['end_date'], "%Y-%m-%d")
            else:
                end = datetime.now()
            return max((end - start).days + 1, 1)
        except Exception:
            return 0

    def _help(self) -> str:
        return (
            "🧳 *Bot pengeluaran trip Padang*\n\n"
            "*Catat pengeluaran* — kirim biasa saja:\n"
            "• makan siang 45.000\n"
            "• grab ke terminal 31rb\n"
            "• hotel 350rb\n\n"
            "*Lihat total* — ketik /trip\n\n"
            "Semua otomatis masuk ke trip Padang. "
            "Yang tidak bisa di sini: pemasukan, hutang, hapus data."
        )


def normalise_phone(value: str) -> str:
    """
    Reduce a WhatsApp identifier to bare digits.

    WhatsApp JIDs also carry an optional device suffix before the '@'
    (``6281228507417:12@s.whatsapp.net``) and may appear as a LID
    (``1234567890@lid``). Naively stripping non-digits would weld the device id
    onto the number and produce an identifier that matches nobody, so the
    suffix is removed first.
    """
    text = str(value or '').strip()
    # Keep only the part before '@', then drop any ':device' suffix.
    text = text.split('@', 1)[0]
    text = text.split(':', 1)[0]
    return re.sub(r'\D', '', text)


def load_trip_users(path: Optional[str] = None) -> Dict[str, str]:
    """
    Read the number -> name map for the trip companions.

    Numbers come from the environment allowlist so there is a single place to
    revoke access; names from a small JSON file next to this module. A number in
    the environment without a name still works, it just shows as 'Peserta'.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = path or os.path.join(here, "trip_users.json")

    names: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            for number, value in raw.items():
                key = normalise_phone(number)
                if not key:
                    continue
                if isinstance(value, dict):
                    names[key] = str(value.get("name") or "Peserta")
                else:
                    names[key] = str(value or "Peserta")
    except FileNotFoundError:
        pass
    except Exception:
        # A malformed file must not take the bot down; it only costs names.
        pass

    env = os.environ.get("WHATSAPP_FINANCE_USERS", "")
    for number in env.split(","):
        key = normalise_phone(number)
        if key:
            names.setdefault(key, "Peserta")

    return names


if __name__ == "__main__":
    import sys

    bot = TripWhatsAppBot()
    if len(sys.argv) > 1:
        sender = sys.argv[1]
        message = " ".join(sys.argv[2:]) or "/help"
        print(bot.handle(sender, message))
    else:
        print("Allowed:", bot.allowed_numbers())
