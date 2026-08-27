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
            with open(schema_path, 'r') as f:
                cursor.executescript(f.read())
            
            conn.commit()
            conn.close()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== TRANSAKSI ====================
    
    def add_expense(self, amount: int, category: str, description: str = "", date: Optional[str] = None) -> bool:
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
            
            cursor.execute(
                "INSERT INTO transactions (amount, type, category_id, description, date) VALUES (?, ?, ?, ?, ?)",
                (amount, 'expense', category_id, description, date)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def add_income(self, amount: int, source: str, category: str = "Lainnya (Pemasukan)", date: Optional[str] = None) -> bool:
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
            'source': source
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
    
    def get_expense_by_category(self, month: Optional[str] = None) -> List[Dict]:
        """Pengeluaran per kategori untuk bulan tertentu"""
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        start_date = f"{month}-01"
        
        # Hitung hari terakhir bulan
        year, month_num = map(int, month.split('-'))
        if month_num == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month_num + 1:02d}-01"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT c.name, SUM(t.amount) as total 
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense' AND t.date >= ? AND t.date < ?
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
