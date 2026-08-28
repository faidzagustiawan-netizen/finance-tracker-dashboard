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
        if not os.path.exists(self.db_path):
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
                
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== TRANSAKSI ====================
    
    def add_expense(self, amount: int, category: str, description: str = "", date: Optional[str] = None, account_id: Optional[int] = None) -> bool:
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
            
            category_id = result[0]
            
            if account_id is not None:
                cursor.execute(
                    "INSERT INTO transactions (amount, type, category_id, description, date, account_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (amount, 'expense', category_id, description, date, account_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO transactions (amount, type, category_id, description, date) VALUES (?, ?, ?, ?, ?)",
                    (amount, 'expense', category_id, description, date)
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
            if account_id is not None:
                cursor.execute(
                    "INSERT INTO transactions (amount, type, category_id, description, date, account_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (amount, 'income', category_id, source, date, account_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO transactions (amount, type, category_id, description, date) VALUES (?, ?, ?, ?, ?)",
                    (amount, 'income', category_id, source, date)
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
    
    def parse_transaction_input(self, text: str) -> Optional[Dict]:
        """
        Parse input chat untuk transaksi
        Format: "25rb makanan" atau "jajan 50k" atau "gajian 5jt sumber: freelance"
        """
        text = text.strip().lower()
        
        # Pattern untuk amount
        amount_pattern = r'(\d+(?:\.\d+)?)\s*([rk]b?|juta?|jt)'
        
        match = re.search(amount_pattern, text)
        if not match:
            return None
        
        amount_str = match.group(1)
        unit = match.group(2).lower()
        
        # Convert ke Rupiah
        amount = float(amount_str)
        if 'jt' in unit or 'juta' in unit:
            amount = int(amount * 1_000_000)
        elif 'rb' in unit or 'k' in unit:
            amount = int(amount * 1_000)
        else:
            amount = int(amount)
        
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
        
        # Deteksi tipe (income/expense)
        income_keywords = ['gajian', 'gaji', 'freelance', 'bonus', 'proyek', 'project', 'dapat']
        is_income = any(kw in remaining for kw in income_keywords)
        
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
