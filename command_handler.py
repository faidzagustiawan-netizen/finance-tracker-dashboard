import re
from datetime import datetime
from finance_tracker import FinanceTracker
from typing import Optional, Tuple

class FinanceCommandHandler:
    def __init__(self, db_path: str = "finance.db"):
        self.tracker = FinanceTracker(db_path)
    
    def handle_message(self, text: str) -> str:
        """
        Parse dan handle pesan dari WhatsApp
        Return: response message
        """
        text = text.strip()
        
        # Command dengan slash
        if text.startswith('/'):
            return self.handle_command(text)
        
        # Natural language input
        return self.handle_natural_input(text)
    
    def handle_command(self, text: str) -> str:
        """Handle /command format"""
        parts = text.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Report commands
        if command == '/balance':
            return self.cmd_balance()
        elif command == '/expenses':
            return self.cmd_expenses(args)
        elif command == '/income':
            return self.cmd_income(args)
        elif command == '/debts':
            return self.cmd_all_debts()
        elif command == '/debt':
            return self.cmd_friend_debt(args)
        elif command == '/categories':
            return self.cmd_categories()
        elif command == '/help':
            return self.cmd_help()
        else:
            return "❌ Perintah tidak dikenal. Ketik /help untuk melihat bantuan."
    
    def handle_natural_input(self, text: str) -> str:
        """
        Handle natural language input
        Contoh:
        - "25rb makanan"
        - "jajan 50k"
        - "gajian 5jt sumber: freelance"
        - "hutang ke budi 100rb makan bareng"
        - "budi hutang ke saya 50rb kopi"
        - "bayar hutang ke budi 50rb"
        """
        
        # Deteksi pembayaran hutang DULU (karena mengandung kata "hutang")
        payment_match = re.search(r'bayar\s+(.*\s)?hutang', text, re.IGNORECASE)
        if payment_match:
            return self.parse_debt_payment(text)
        
        # Deteksi hutang/piutang
        debt_match = re.search(r'(hutang|piutang)', text, re.IGNORECASE)
        if debt_match:
            return self.parse_debt_input(text)
        
        # Transaksi biasa
        return self.parse_transaction_input(text)
    
    def parse_transaction_input(self, text: str) -> str:
        """Parse normal transaction input"""
        parsed = self.tracker.parse_transaction_input(text)
        
        if not parsed:
            return "❌ Format tidak dikenal. Contoh: '25rb makanan', 'gajian 5jt'"
        
        amount = parsed['amount']
        trans_type = parsed['type']
        category_hint = parsed['category_hint']
        description = parsed['description']
        
        # Deteksi kategori
        if trans_type == 'income':
            category = self.match_category(category_hint, 'income')
            if not category:
                category = "Lainnya (Pemasukan)"
            
            try:
                success = self.tracker.add_income(
                    amount=amount,
                    source=description,
                    category=category,
                    date=datetime.now().strftime("%Y-%m-%d")
                )
                
                if success:
                    return f"✅ Pemasukan dicatat: Rp {amount:,} ({category})\nSumber: {description}"
                else:
                    return "❌ Gagal mencatat pemasukan"
            except Exception as e:
                return f"❌ Error: {str(e)}"
        
        else:  # expense
            category = self.match_category(category_hint, 'expense')
            if not category:
                category = "Lainnya"
            
            try:
                success = self.tracker.add_expense(
                    amount=amount,
                    category=category,
                    description=description,
                    date=datetime.now().strftime("%Y-%m-%d")
                )
                
                if success:
                    return f"✅ Pengeluaran dicatat: Rp {amount:,} ({category})"
                else:
                    return "❌ Gagal mencatat pengeluaran"
            except Exception as e:
                return f"❌ Error: {str(e)}"
    
    def parse_debt_input(self, text: str) -> str:
        """
        Parse hutang/piutang
        Contoh:
        - "hutang ke budi 100rb makan bareng"
        - "budi hutang ke saya 50rb"
        - "piutang dari budi 200rb"
        """
        
        # Deteksi tipe hutang dengan pattern spesifik
        # Priority: check "hutang ke saya" / "piutang dari" DULU (piutang saya)
        # IMPORTANT: Match "hutang ke saya" (bukan hanya "hutang ke")
        is_owed = bool(re.search(r'hutang\s+ke\s+saya|piutang\s+dari', text, re.IGNORECASE))
        
        # Jika tidak owed, check "hutang ke [bukan saya]" atau "saya hutang ke"
        # IMPORTANT: Make sure it's NOT "hutang ke saya"
        is_owe = bool(re.search(r'(?:saya\s+)?hutang\s+ke\s+(?!saya)', text, re.IGNORECASE))
        
        if not is_owe and not is_owed:
            # Default: anggap "hutang" tanpa preposisi = hutang ke teman
            is_owe = True
        
        # Extract nama teman dari berbagai pattern
        friend_name = None
        
        if is_owe:
            # Pattern: "hutang ke [nama]" atau "saya hutang ke [nama]"
            match = re.search(r'(?:saya\s+)?hutang\s+ke\s+(\w+)', text, re.IGNORECASE)
            if match:
                friend_name = match.group(1)
        
        if is_owed and not friend_name:
            # Pattern: "[nama] hutang ke saya" atau "piutang dari [nama]"
            match = re.search(r'(\w+)\s+hutang\s+ke\s+saya', text, re.IGNORECASE)
            if not match:
                match = re.search(r'piutang\s+dari\s+(\w+)', text, re.IGNORECASE)
            if match:
                friend_name = match.group(1)
        
        if not friend_name:
            return "❌ Siapa nama temannya? Contoh: 'hutang ke budi 100rb' atau 'budi hutang ke saya 50rb'"
        
        friend_name = friend_name.lower()
        
        # Extract amount
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*([rk]b?|juta?|jt)', text, re.IGNORECASE)
        if not amount_match:
            return "❌ Berapa jumlahnya? Contoh: '50rb', '1jt'"
        
        amount_str = amount_match.group(1)
        unit = amount_match.group(2).lower()
        
        amount = float(amount_str)
        if 'jt' in unit or 'juta' in unit:
            amount = int(amount * 1_000_000)
        elif 'rb' in unit or 'k' in unit:
            amount = int(amount * 1_000)
        else:
            amount = int(amount)
        
        # Extract description (text setelah amount)
        desc_match = re.search(r'(\d+[rk]b?|juta?|jt)\s+(.+?)(?:\s*$)', text, re.IGNORECASE)
        description = desc_match.group(2) if desc_match else ""
        
        # Determine debt type based on detection
        debt_type = 'owe' if is_owe else 'owed'
        msg_type = "hutang ke" if is_owe else "piutang dari"
        
        success = self.tracker.add_debt(
            friend_name=friend_name,
            amount=amount,
            debt_type=debt_type,
            description=description,
            date=datetime.now().strftime("%Y-%m-%d")
        )
        
        if success:
            msg = f"✅ {msg_type.capitalize()} {friend_name.capitalize()}: Rp {amount:,}"
            if description:
                msg += f"\n({description})"
            return msg
        else:
            return "❌ Gagal mencatat hutang"
    
    def parse_debt_payment(self, text: str) -> str:
        """
        Parse pembayaran hutang
        Contoh: "bayar hutang ke budi 50rb"
        """
        return "⏳ Fitur pembayaran hutang masih dalam development"
    
    def match_category(self, hint: str, trans_type: str) -> Optional[str]:
        """Match hint dengan kategori yang ada"""
        hint_lower = hint.lower()
        categories = self.tracker.get_categories(trans_type)
        
        # Keyword map untuk matching
        keyword_map = {
            'expense': {
                'Makanan': ['makanan', 'makan', 'jajan', 'kopi', 'sarapan', 'siang', 'malam', 'minum'],
                'Transport': ['transport', 'bensin', 'ojek', 'taksi', 'bis', 'kereta', 'grab', 'gojek', 'motor'],
                'Tagihan': ['tagihan', 'listrik', 'air', 'internet', 'bayar', 'cicilan'],
                'Hiburan': ['hiburan', 'bioskop', 'game', 'spotify', 'konser', 'nonton'],
                'Belanja': ['belanja', 'baju', 'sepatu', 'laptop', 'elektronik', 'pakaian'],
                'Kesehatan': ['kesehatan', 'dokter', 'obat', 'apotek', 'rumah sakit'],
            },
            'income': {
                'Gaji': ['gaji', 'gajian'],
                'Freelance': ['freelance', 'project', 'proyek', 'jasa', 'design'],
                'Bonus': ['bonus', 'tunjangan'],
            }
        }
        
        # Keyword match
        if trans_type in keyword_map:
            for category, keywords in keyword_map[trans_type].items():
                for kw in keywords:
                    if kw in hint_lower:
                        # Verify category exists
                        if category in categories:
                            return category
        
        return None
    
    # ==================== COMMANDS ====================
    
    def cmd_balance(self) -> str:
        """/balance - Lihat balance bulan ini"""
        balance = self.tracker.get_balance()
        
        return f"""💰 **BALANCE BULAN INI**
        
Pemasukan: Rp {balance['income']:,}
Pengeluaran: Rp {balance['expense']:,}
─────────────
Balance: Rp {balance['balance']:,} {'✅' if balance['balance'] >= 0 else '⚠️'}"""
    
    def cmd_expenses(self, args: list) -> str:
        """
        /expenses [bulan] - Lihat pengeluaran per kategori
        Contoh: /expenses 2026-08
        """
        month = args[0] if args else datetime.now().strftime("%Y-%m")
        
        try:
            expenses = self.tracker.get_expense_by_category(month)
        except:
            return "❌ Format bulan salah. Contoh: /expenses 2026-08"
        
        if not expenses:
            return f"Tidak ada pengeluaran di bulan {month}"
        
        total = sum(e['total'] for e in expenses)
        
        msg = f"📊 **PENGELUARAN BULAN {month}**\n\n"
        for exp in expenses:
            percentage = (exp['total'] / total * 100) if total > 0 else 0
            msg += f"• {exp['name']}: Rp {exp['total']:,} ({percentage:.1f}%)\n"
        
        msg += f"\n─────────────\nTotal: Rp {total:,}"
        return msg
    
    def cmd_income(self, args: list) -> str:
        """
        /income [bulan] - Lihat pemasukan detail
        """
        month = args[0] if args else datetime.now().strftime("%Y-%m")
        return "⏳ Fitur income detail masih dalam development"
    
    def cmd_all_debts(self) -> str:
        """
        /debts - Lihat semua hutang/piutang pending
        """
        debts = self.tracker.get_all_pending_debts()
        
        if not debts:
            return "✅ Tidak ada hutang/piutang yang pending!"
        
        msg = "💳 **HUTANG/PIUTANG PENDING**\n\n"
        
        total_owe = 0
        total_owed = 0
        
        current_friend = None
        for debt in debts:
            if debt['friend_name'] != current_friend:
                if current_friend:
                    msg += "\n"
                current_friend = debt['friend_name']
            
            if debt['type'] == 'owe':
                msg += f"• Saya HUTANG ke {debt['friend_name'].capitalize()}: Rp {debt['amount']:,}\n"
                total_owe += debt['amount']
            else:
                msg += f"• {debt['friend_name'].capitalize()} HUTANG ke saya: Rp {debt['amount']:,}\n"
                total_owed += debt['amount']
        
        msg += f"\n─────────────\n"
        msg += f"Total hutang saya: Rp {total_owe:,}\n"
        msg += f"Total yang saya terima: Rp {total_owed:,}\n"
        msg += f"Net balance: Rp {total_owed - total_owe:,}"
        
        return msg
    
    def cmd_friend_debt(self, args: list) -> str:
        """
        /debt [nama teman] - Lihat hutang/piutang dengan teman tertentu
        """
        if not args:
            return "❌ Siapa nama temannya? Contoh: /debt budi"
        
        friend_name = args[0].lower()
        debts = self.tracker.get_friend_debts(friend_name)
        
        msg = f"💳 **HUTANG/PIUTANG DENGAN {friend_name.upper()}**\n\n"
        
        if not debts['owe'] and not debts['owed']:
            return f"✅ Tidak ada hutang/piutang dengan {friend_name}!"
        
        if debts['owe']:
            total_owe = sum(d['amount'] for d in debts['owe'])
            msg += f"Saya hutang: Rp {total_owe:,}\n"
            for debt in debts['owe']:
                msg += f"  - Rp {debt['amount']:,} ({debt['date']})\n"
        
        if debts['owed']:
            total_owed = sum(d['amount'] for d in debts['owed'])
            msg += f"\n{friend_name.capitalize()} hutang ke saya: Rp {total_owed:,}\n"
            for debt in debts['owed']:
                msg += f"  - Rp {debt['amount']:,} ({debt['date']})\n"
        
        return msg
    
    def cmd_categories(self) -> str:
        """
        /categories - Lihat daftar kategori
        """
        expense_cats = self.tracker.get_categories('expense')
        income_cats = self.tracker.get_categories('income')
        
        msg = "📋 **KATEGORI TERSEDIA**\n\n"
        msg += "**Pengeluaran:**\n"
        for cat in expense_cats:
            msg += f"• {cat}\n"
        
        msg += "\n**Pemasukan:**\n"
        for cat in income_cats:
            msg += f"• {cat}\n"
        
        return msg
    
    def cmd_help(self) -> str:
        """
        /help - Bantuan penggunaan
        """
        return """📖 **BANTUAN FINANCE TRACKER**

**Format Natural (tanpa slash):**
• _Pengeluaran:_ "25rb makanan" / "jajan 50k"
• _Pemasukan:_ "gajian 5jt" / "freelance 500rb"
• _Hutang:_ "hutang ke budi 100rb" / "budi hutang ke saya 50rb"

**Commands:**
• /balance - Balance bulan ini
• /expenses [bulan] - Pengeluaran per kategori (contoh: /expenses 2026-08)
• /debts - Semua hutang/piutang
• /debt [nama] - Hutang/piutang dengan teman tertentu
• /categories - Lihat daftar kategori
• /help - Bantuan ini

**Format Tanggal:** YYYY-MM-DD
**Format Uang:** 25rb, 50k, 1jt, 2juta"""
