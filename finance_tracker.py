import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import re

class FinanceTracker:
    def __init__(self, db_path: str = "finance.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database dengan schema"""
        # Check whether the schema is actually present rather than whether the
        # file exists: a zero-byte file (or a temp path created ahead of time)
        # would otherwise skip this and every later migration would fail on a
        # missing table.
        conn = sqlite3.connect(self.db_path)
        try:
            has_schema = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='transactions'"
            ).fetchone()
        finally:
            conn.close()

        if not has_schema:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Baca schema dari file
            schema_path = Path(__file__).parent / "schema.sql"
            with open(schema_path, 'r', encoding='utf-8') as f:
                cursor.executescript(f.read())

            conn.commit()
            conn.close()
        self.migrate_db()
        
    def migrate_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Add account_id column to transactions if not exists
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [info['name'] for info in cursor.fetchall()]
        if 'account_id' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN account_id INTEGER REFERENCES accounts(id)")
        
        # Create accounts table if not exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
        if not cursor.fetchone():
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('bank', 'ewallet', 'cash')),
                icon TEXT DEFAULT '',
                color TEXT DEFAULT '#3b82f6',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            default_accounts = [
                ('Cash', 'cash', '💵', '#22c55e'),
                ('BRI', 'bank', '🏦', '#1d4ed8'),
                ('ShopeePay', 'ewallet', '🟠', '#f97316'),
                ('GoPay', 'ewallet', '🟢', '#22d3ee'),
                ('SeaBank', 'bank', '🌊', '#0ea5e9')
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO accounts (name, type, icon, color) VALUES (?, ?, ?, ?)",
                default_accounts
            )
        
        # Create index after column is ensured
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)")
        except Exception:
            pass

        # Trip tagging. A trip is a named period with an end date; expenses in
        # that window can be reported as a group ("how much did Padang cost?"),
        # which is the question that actually matters when travelling.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                start_date DATE NOT NULL,
                end_date DATE,
                budget INTEGER,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'done')),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [info['name'] for info in cursor.fetchall()]
        if 'trip_id' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN trip_id INTEGER REFERENCES trips(id)")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_trip ON transactions(trip_id)")
        except Exception:
            pass

        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== TRIP ====================

    def create_trip(self, name: str, start_date: Optional[str] = None,
                    end_date: Optional[str] = None, budget: Optional[int] = None,
                    notes: str = "") -> Optional[int]:
        """Buat trip baru. Return trip id, atau None kalau slug sudah ada."""
        start_date = start_date or datetime.now().strftime("%Y-%m-%d")
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower().strip()).strip('-')

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO trips (name, slug, start_date, end_date, budget, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, slug, start_date, end_date, budget, notes)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_trip(self, ref: str) -> Optional[Dict]:
        """Cari trip dari slug, nama, atau id."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM trips
                   WHERE slug = ? OR lower(name) = ? OR id = ?
                   ORDER BY id DESC LIMIT 1""",
                (ref.lower().strip(), ref.lower().strip(),
                 int(ref) if ref.strip().isdigit() else -1)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_active_trip(self) -> Optional[Dict]:
        """
        Trip yang sedang berjalan: yang aktif dan tanggal hari ini masih di
        dalam rentangnya (atau belum punya end_date). Dipakai supaya pengeluaran
        otomatis nempel ke trip tanpa perlu ditag setiap kali.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                """SELECT * FROM trips
                   WHERE status = 'active'
                     AND start_date <= ?
                     AND (end_date IS NULL OR end_date >= ?)
                   ORDER BY start_date DESC LIMIT 1""",
                (today, today)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def end_trip(self, ref: str, end_date: Optional[str] = None) -> bool:
        """Tutup trip: set status done + end_date."""
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        trip = self.get_trip(ref)
        if not trip:
            return False

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE trips SET status = 'done', end_date = ? WHERE id = ?",
                (end_date, trip['id'])
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_trip_summary(self, trip_id: int) -> Dict:
        """Total + breakdown per kategori untuk satu trip."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT COALESCE(SUM(amount), 0) FROM transactions
                   WHERE trip_id = ? AND type = 'expense'""",
                (trip_id,)
            )
            total = cursor.fetchone()[0] or 0

            cursor.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM transactions
                   WHERE trip_id = ? AND type = 'income'""",
                (trip_id,)
            )
            income, income_count = cursor.fetchone()

            cursor.execute(
                """SELECT c.name, SUM(t.amount) AS total, COUNT(*) AS n
                   FROM transactions t
                   LEFT JOIN categories c ON t.category_id = c.id
                   WHERE t.trip_id = ? AND t.type = 'expense'
                   GROUP BY c.name ORDER BY total DESC""",
                (trip_id,)
            )
            by_category = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                """SELECT t.id, t.date, t.amount, c.name AS category, t.description
                   FROM transactions t
                   LEFT JOIN categories c ON t.category_id = c.id
                   WHERE t.trip_id = ?
                   ORDER BY t.date DESC, t.id DESC""",
                (trip_id,)
            )
            items = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE trip_id = ? AND type = 'expense'",
                (trip_id,)
            )
            expense_count = cursor.fetchone()[0]

            return {
                'total': total,
                'expense_count': expense_count,
                'income': income,
                'income_count': income_count,
                'by_category': by_category,
                'items': items,
            }
        finally:
            conn.close()

    def list_trips(self, include_done: bool = True) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = """SELECT t.*,
                              (SELECT COALESCE(SUM(amount), 0) FROM transactions
                                WHERE trip_id = t.id AND type = 'expense') AS total,
                              (SELECT COUNT(*) FROM transactions
                                WHERE trip_id = t.id AND type = 'expense') AS n
                       FROM trips t"""
            if not include_done:
                query += " WHERE t.status = 'active'"
            query += " ORDER BY t.start_date DESC, t.id DESC"
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== TRANSAKSI ====================

    def _resolve_account(self, cursor, account_id: Optional[int]) -> Optional[int]:
        """
        Return an account id that actually exists.

        The transactions table carries "account_id INTEGER DEFAULT 1", but the
        seeded accounts start at id 2 (Cash), so a row inserted without an
        explicit account silently points at nothing and is invisible to every
        per-account total. Fall back to Cash rather than leaving a dangling id.
        """
        if account_id is not None:
            cursor.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
            if cursor.fetchone():
                return account_id

        cursor.execute(
            "SELECT id FROM accounts WHERE lower(name) = 'cash' ORDER BY id LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        cursor.execute("SELECT id FROM accounts ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    def add_expense(self, amount: int, category: str, description: str = "", date: Optional[str] = None, account_id: Optional[int] = None, trip_id: Optional[int] = None) -> bool:
        """
        Tambah pengeluaran
        amount: dalam Rupiah (integer)
        category: nama kategori
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Ambil category_id
            cursor.execute("SELECT id FROM categories WHERE name = ? AND type = 'expense'", (category,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            account_id = self._resolve_account(cursor, account_id)
            category_id = result[0]

            cursor.execute(
                "INSERT INTO transactions (amount, type, category_id, description, date, account_id, trip_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (amount, 'expense', category_id, description, date, account_id, trip_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def add_income(self, amount: int, source: str, category: str = "Lainnya (Pemasukan)", date: Optional[str] = None, account_id: Optional[int] = None) -> bool:
        """
        Tambah pemasukan
        amount: dalam Rupiah
        source: dari mana (misal: "Freelance project X", "Gaji bulanan")
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Ambil category_id
            cursor.execute("SELECT id FROM categories WHERE name = ? AND type = 'income'", (category,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            category_id = result[0]
            
            # Insert transaction
            account_id = self._resolve_account(cursor, account_id)
            cursor.execute(
                "INSERT INTO transactions (amount, type, category_id, description, date, account_id) VALUES (?, ?, ?, ?, ?, ?)",
                (amount, 'income', category_id, source, date, account_id)
            )
            transaction_id = cursor.lastrowid
            
            # Insert income source
            cursor.execute(
                "INSERT INTO income_sources (transaction_id, source) VALUES (?, ?)",
                (transaction_id, source)
            )
            conn.commit()
            return True
        finally:
            conn.close()
            
    def update_transaction(self, tx_id: int, amount: Optional[int] = None, description: Optional[str] = None, category_name: Optional[str] = None, account_id: Optional[int] = None, date: Optional[str] = None) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Check if transaction exists
            cursor.execute("SELECT id, type FROM transactions WHERE id = ?", (tx_id,))
            tx = cursor.fetchone()
            if not tx:
                return False
                
            tx_type = tx['type']
            
            updates = []
            params = []
            
            if amount is not None:
                updates.append("amount = ?")
                params.append(amount)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if date is not None:
                updates.append("date = ?")
                params.append(date)
            if account_id is not None:
                updates.append("account_id = ?")
                params.append(account_id)
            if category_name is not None:
                cursor.execute("SELECT id FROM categories WHERE name = ? AND type = ?", (category_name, tx_type))
                cat = cursor.fetchone()
                if cat:
                    updates.append("category_id = ?")
                    params.append(cat[0])
            
            if updates:
                query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
                params.append(tx_id)
                cursor.execute(query, params)
                conn.commit()
            return True
        finally:
            conn.close()
            
    def get_accounts(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY created_at")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
            
    def get_account_balances(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    account_id,
                    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
                FROM transactions
            """
            params = []
            if start_date and end_date:
                query += " WHERE date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            
            query += " GROUP BY account_id"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # Matches a rupiah amount written any of the usual ways inside free text.
    # Kept deliberately loose about separators because "40.000" and "40,000"
    # both mean forty thousand here, not forty point zero.
    _AMOUNT_RE = re.compile(
        r'(?<![\w.])'                      # start at a word boundary, not mid-number
        r'(?:rp\.?\s*)?'                   # optional "rp" / "rp."
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+)'  # 40.000 / 40,000 / 1.5 / 40000
        r'\s*'
        r'(ribu|rb|juta|jt|k)?'            # optional magnitude suffix
        r'(?![\w.])',
        re.IGNORECASE,
    )

    # Values that are obviously not money amounts -- a bare year, a count, or a
    # duration. Without this, "makan 2 hari 40rb" would silently pick "2".
    _NOT_AMOUNT = {0, 1}

    def _extract_amount(self, text: str):
        """
        Pull the rupiah amount out of free text.

        Returns (match, amount_in_rupiah), or (None, None) when nothing that
        looks like an amount is present.
        """
        for m in self._AMOUNT_RE.finditer(text):
            raw, unit = m.group(1), (m.group(2) or "").lower()

            # For a bare integer with no unit and no group separators, drop the
            # obvious non-amounts. A separated number ("40.000") is always money.
            separated = bool(re.search(r'[.,]', raw))
            digits = raw.replace(".", "").replace(",", "")

            if not unit and not separated:
                value = int(digits)
                if value < 100:          # "2 hari", "3 kali" -- too small for rupiah
                    continue
                return m, value

            # Normalise the number. If a separator is followed by 3 digits it is a
            # thousands separator ("40.000"); otherwise it is a decimal point
            # ("1.5jt"). Indonesian format is dot-grouped, so prefer that reading.
            normalised = self._normalise_number(raw)

            if unit in ("ribu", "rb", "k"):
                amount = int(normalised * 1_000)
            elif unit in ("juta", "jt"):
                amount = int(normalised * 1_000_000)
            else:
                amount = int(normalised)      # already grouped, e.g. "40.000"

            if amount <= 0:
                continue
            return m, amount

        return None, None

    @staticmethod
    def _normalise_number(raw: str) -> float:
        """Turn '40.000' / '40,000' / '1.5' / '1,5' into a float."""
        has_dot, has_comma = '.' in raw, ',' in raw

        if has_dot and has_comma:
            # Whichever separator comes last is the decimal one.
            if raw.rfind(',') > raw.rfind('.'):
                return float(raw.replace(".", "").replace(",", "."))
            return float(raw.replace(",", ""))

        for sep in ('.', ','):
            if sep in raw:
                head, _, tail = raw.rpartition(sep)
                # A 3-digit tail means grouping; anything else is a decimal.
                if len(tail) == 3 and head:
                    return float(raw.replace(sep, ""))
                return float(raw.replace(sep, "."))

        return float(raw)

    def parse_transaction_input(self, text: str) -> Optional[Dict]:
        """
        Parse input chat untuk transaksi
        Format: "25rb makanan" atau "jajan 50k" atau "gajian 5jt sumber: freelance"
        """
        text = text.strip().lower()

        # Find the amount. People write rupiah many ways -- "40000", "40.000",
        # "40,000", "40rb", "40ribu", "40k", "2jt", "2 juta", "1.5jt" -- and the
        # old pattern only understood the "40rb" style, silently rejecting the
        # plain and dot-grouped forms that are the most natural thing to type.
        match, amount = self._extract_amount(text)
        if match is None:
            return None

        # Ambil sisa text sebagai description/category
        remaining = text[:match.start()] + text[match.end():]
        remaining = remaining.strip()
        
        # Deteksi akun
        accounts = self.get_accounts()
        account_id = None
        
        accounts.sort(key=lambda x: len(x['name']), reverse=True)
        
        for acc in accounts:
            name_lower = acc['name'].lower()
            if name_lower in remaining:
                account_id = acc['id']
                remaining = remaining.replace(name_lower, '').strip()
                break
                
        # Alias khusus untuk shopeepay
        if not account_id and 'spay' in remaining:
            for acc in accounts:
                if acc['name'].lower() == 'shopeepay':
                    account_id = acc['id']
                    remaining = remaining.replace('spay', '').strip()
                    break
                    
        # Bersihkan kata sambung
        remaining = re.sub(r'\b(?:di|ke|masuk|dompet)\b', '', remaining).strip()
        remaining = re.sub(r'\s+', ' ', remaining)
        
        # Deteksi tipe (income/expense) - comprehensive Indonesian keywords
        income_keywords = [
            'gajian', 'gaji', 'freelance', 'bonus', 'proyek', 'project', 'dapat', 
            'nfd', 'transfer masuk', 'kiriman', 'pinjaman', 'dapet', 'terima', 
            'masuk', 'income', 'earn', 'upah', 'honor', 'fee', 'komisi', 'royalti',
            'refund', 'return', 'bayar balik', 'lunasi', 'setor', 'deposit'
        ]
        expense_keywords = [
            'jajan', 'makan', 'bensin', 'listrik', 'bayar', 'beli', 'belanja', 
            'cicilan', 'sewa', 'kopi', 'minum', 'rokok', 'pulsa', 'internet', 
            'tagihan', 'iuran', 'biaya', 'ongkos', 'transport', 'taksi', 'ojek',
            'potong', 'minus', 'kurang', 'expense', 'spending', 'mahal', 'habis',
            'boros', 'langganan', 'berlangganan', 'donasi', 'umroh', 'liburan'
        ]
        
        is_income = any(kw in remaining for kw in income_keywords)
        is_expense = any(kw in remaining for kw in expense_keywords)
        
        # Default ke expense jika tidak ada keyword match
        if not is_income and not is_expense:
            is_income = False  # Default expense
        elif is_income and is_expense:
            # If both, check position - closer keyword wins
            income_pos = min([remaining.find(kw) for kw in income_keywords if kw in remaining], default=999)
            expense_pos = min([remaining.find(kw) for kw in expense_keywords if kw in remaining], default=999)
            is_income = income_pos < expense_pos
        
        # Deteksi source untuk income
        source = remaining
        if 'sumber:' in remaining:
            parts = remaining.split('sumber:')
            remaining = parts[0].strip()
            source = parts[1].strip()
        
        return {
            'amount': amount,
            'type': 'income' if is_income else 'expense',
            'category_hint': remaining,
            'description': remaining,
            'source': source,
            'account_id': account_id
        }
    
    # ==================== HUTANG-PIUTANG ====================
    
    def add_debt(self, friend_name: str, amount: int, debt_type: str, description: str = "", date: Optional[str] = None) -> bool:
        """
        Tambah hutang/piutang
        debt_type: 'owe' (saya hutang), 'owed' (teman hutang ke saya)
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if debt_type not in ['owe', 'owed']:
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO debts (friend_name, amount, type, description, date) VALUES (?, ?, ?, ?, ?)",
                (friend_name, amount, debt_type, description, date)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def pay_debt(self, debt_id: int, amount: int, date: Optional[str] = None) -> bool:
        """Bayar sebagian atau seluruh hutang"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Ambil data hutang
            cursor.execute("SELECT amount FROM debts WHERE id = ? AND status = 'pending'", (debt_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            remaining = result[0]
            
            # Insert payment
            cursor.execute(
                "INSERT INTO debt_payments (debt_id, amount, payment_date) VALUES (?, ?, ?)",
                (debt_id, amount, date)
            )
            
            # Update status jika sudah lunas
            new_remaining = remaining - amount
            if new_remaining <= 0:
                cursor.execute(
                    "UPDATE debts SET status = 'settled', settled_date = ? WHERE id = ?",
                    (date, debt_id)
                )
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_friend_debts(self, friend_name: str) -> Dict:
        """Lihat hutang/piutang dengan teman tertentu"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Hutang saya ke teman
            cursor.execute("""
                SELECT id, amount, date FROM debts 
                WHERE friend_name = ? AND type = 'owe' AND status = 'pending'
            """, (friend_name,))
            owe = cursor.fetchall()
            
            # Piutang saya dari teman
            cursor.execute("""
                SELECT id, amount, date FROM debts 
                WHERE friend_name = ? AND type = 'owed' AND status = 'pending'
            """, (friend_name,))
            owed = cursor.fetchall()
            
            return {
                'friend': friend_name,
                'owe': [dict(row) for row in owe],
                'owed': [dict(row) for row in owed]
            }
        finally:
            conn.close()
    
    # ==================== REPORT ====================
    
    def get_balance(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """
        Hitung balance (pemasukan - pengeluaran)
        Jika tidak ada tanggal, ambil bulan ini
        """
        if not start_date:
            today = datetime.now()
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Total income
            cursor.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE type = 'income' AND date BETWEEN ? AND ?
            """, (start_date, end_date))
            income = cursor.fetchone()[0] or 0
            
            # Total expense
            cursor.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE type = 'expense' AND date BETWEEN ? AND ?
            """, (start_date, end_date))
            expense = cursor.fetchone()[0] or 0
            
            balance = income - expense
            
            return {
                'period': f"{start_date} to {end_date}",
                'income': income,
                'expense': expense,
                'balance': balance
            }
        finally:
            conn.close()
    
    def get_expense_by_category(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Pengeluaran per kategori untuk range waktu tertentu"""
        if not start_date:
            today = datetime.now()
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT c.name, SUM(t.amount) as total 
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND t.date BETWEEN ? AND ?
                GROUP BY c.name
                ORDER BY total DESC
            """, (start_date, end_date))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_all_pending_debts(self) -> List[Dict]:
        """Lihat semua hutang/piutang yang pending"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, friend_name, amount, type, date 
                FROM debts 
                WHERE status = 'pending'
                ORDER BY friend_name, date
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_categories(self, trans_type: str = None) -> List[str]:
        """Ambil daftar kategori"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if trans_type:
                cursor.execute("SELECT name FROM categories WHERE type = ? ORDER BY name", (trans_type,))
            else:
                cursor.execute("SELECT name FROM categories ORDER BY type, name")
            
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
