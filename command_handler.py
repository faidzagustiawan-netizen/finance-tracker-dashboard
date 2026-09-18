import re
from datetime import datetime
from finance_tracker import FinanceTracker
from typing import Optional, Tuple, Dict, List

class FinanceCommandHandler:
    def __init__(self, db_path: str = "finance.db"):
        self.tracker = FinanceTracker(db_path)
    
    def handle_message(self, text: str, force: bool = False):
        """
        Parse dan handle pesan dari WhatsApp
        Return: response message or confirm dict
        """
        text = text.strip()
        
        # Command dengan slash
        if text.startswith('/'):
            return self.handle_command(text)
        
        # Natural language input
        return self.handle_natural_input(text, force)
    
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
        elif command in ('/trip', '/trips', '/perjalanan'):
            return self.cmd_trip(args)
        elif command == '/categories':
            return self.cmd_categories()
        elif command == '/help':
            return self.cmd_help()
        else:
            return "❌ Perintah tidak dikenal. Ketik /help untuk melihat bantuan."
    
    def handle_natural_input(self, text: str, force: bool = False):
        """
        Handle natural language input
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
        return self.parse_transaction_input(text, force)
    
    def parse_transaction_input(self, text: str, force: bool = False):
        """Parse normal transaction input"""
        parsed = self.tracker.parse_transaction_input(text)
        
        if not parsed:
            return "❌ Format tidak dikenal. Contoh: '25rb makanan', 'gajian 5jt'"
        
        amount = parsed['amount']
        trans_type = parsed['type']
        category_hint = parsed['category_hint']
        description = parsed['description']
        account_id = parsed.get('account_id')
        
        # Deteksi kategori
        if trans_type == 'income':
            category = self.match_category(category_hint, 'income')
            if not category:
                category = "Lainnya (Pemasukan)"
            
            if not force and category == "Lainnya (Pemasukan)" and not account_id:
                return {
                    "action": "confirm",
                    "message": f"Kategori tidak terdeteksi jelas (masuk 'Lainnya (Pemasukan)') dan tujuan masuk ke 'Cash'.\nLanjutkan simpan Pemasukan Rp {amount:,} ini?\nAtau klik 'Batal' dan ketik lebih jelas.",
                    "text": text
                }
            
            try:
                success = self.tracker.add_income(
                    amount=amount,
                    source=description,
                    category=category,
                    account_id=account_id,
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
            
            if not force and category == "Lainnya" and not account_id:
                return {
                    "action": "confirm",
                    "message": f"Kategori tidak terdeteksi (masuk 'Lainnya') dan terpotong dari 'Cash'.\nLanjutkan simpan Pengeluaran Rp {amount:,} ini?\nAtau klik 'Batal' dan ketik lebih spesifik (contoh: 'makan 50rb gopay').",
                    "text": text
                }
            
            try:
                # Anything spent while a trip is running is part of that trip,
                # so the traveller never has to remember to tag it.
                trip = self.tracker.get_active_trip()
                trip_id = trip['id'] if trip else None

                success = self.tracker.add_expense(
                    amount=amount,
                    category=category,
                    description=description,
                    account_id=account_id,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    trip_id=trip_id
                )
                
                if success:
                    return self._expense_reply(amount, category, description, account_id, trip)
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

    def _expense_reply(self, amount: int, category: str, description: str,
                       account_id, trip) -> str:
        """
        Reply for a recorded expense.

        The user explicitly asked for a short confirmation plus the running
        balance, not a transaction list: "tidak perlu memberikan transactions
        seperti ini setiap ada transaksi baru, cukup update balance saja".
        The trip line is added only while a trip is running, because during the
        trip that running total is the number that matters.
        """
        accounts = {a['id']: a['name'] for a in self.tracker.get_accounts()}
        account_name = accounts.get(account_id, 'Cash') if account_id else 'Cash'

        balance = self.tracker.get_balance()

        lines = [
            f"✅ Tercatat: {description or category} — Rp {amount:,}",
            f"📁 {category} · {account_name}",
        ]
        if trip:
            summary = self.tracker.get_trip_summary(trip['id'])
            lines.append(
                f"🧳 {trip['name']}: Rp {summary['total']:,} "
                f"({summary['expense_count']} pengeluaran)"
            )
        lines.append(f"💰 Saldo bulan ini: Rp {balance['balance']:,}")
        return "\n".join(lines)

    def cmd_trip(self, args: list) -> str:
        """
        /trip            - ringkasan trip aktif
        /trip list       - semua trip
        /trip <nama>     - ringkasan trip tertentu
        /trip mulai <nama>   - mulai trip baru
        /trip selesai    - tutup trip aktif
        """
        if not args:
            trip = self.tracker.get_active_trip()
            if not trip:
                return ("🧳 Tidak ada trip aktif.\n\n"
                        "Mulai dengan: `/trip mulai Padang`")
            return self._trip_summary_text(trip, verbose=True)

        sub = args[0].lower()

        if sub in ('list', 'daftar'):
            trips = self.tracker.list_trips()
            if not trips:
                return "🧳 Belum ada trip."
            msg = "🧳 **DAFTAR TRIP**\n"
            for t in trips:
                mark = '🟢' if t['status'] == 'active' else '⚪'
                msg += (f"\n{mark} {t['name']} ({t['start_date']}"
                        f"{' → ' + t['end_date'] if t['end_date'] else ''})\n"
                        f"   Rp {t['total']:,} · {t['n']} pengeluaran")
            return msg

        if sub in ('mulai', 'start', 'baru'):
            name = " ".join(args[1:]).strip()
            if not name:
                return "❌ Contoh: `/trip mulai Padang`"
            existing = self.tracker.get_active_trip()
            if existing:
                self.tracker.end_trip(existing['slug'])
            trip_id = self.tracker.create_trip(name)
            if trip_id is None:
                return f"❌ Trip '{name}' sudah ada."
            return (f"🧳 Trip dimulai: **{name}**\n"
                    f"Semua pengeluaran otomatis masuk ke trip ini sampai "
                    f"kamu ketik `/trip selesai`.")

        if sub in ('selesai', 'end', 'stop', 'tutup'):
            trip = self.tracker.get_active_trip()
            if not trip:
                return "❌ Tidak ada trip aktif."
            self.tracker.end_trip(trip['slug'])
            return ("🧳 Trip ditutup.\n\n"
                    + self._trip_summary_text(trip, verbose=True))

        # Otherwise treat the argument as a trip name
        trip = self.tracker.get_trip(" ".join(args))
        if not trip:
            return f"❌ Trip '{' '.join(args)}' tidak ditemukan."
        return self._trip_summary_text(trip, verbose=True)

    def _trip_summary_text(self, trip: Dict, verbose: bool = False) -> str:
        summary = self.tracker.get_trip_summary(trip['id'])

        msg = f"🧳 **{trip['name'].upper()}**\n"
        msg += f"{trip['start_date']}"
        msg += f" → {trip['end_date']}" if trip['end_date'] else " → sekarang"
        if trip['status'] == 'done':
            msg += " (selesai)"
        msg += "\n"

        if summary['expense_count'] == 0:
            return msg + "\nBelum ada pengeluaran."

        msg += f"\nTotal: Rp {summary['total']:,}"
        days = self._trip_days(trip)
        if days > 0:
            msg += f"\nRata-rata: Rp {summary['total'] // days:,}/hari ({days} hari)"

        if trip.get('budget'):
            left = trip['budget'] - summary['total']
            pct = summary['total'] / trip['budget'] * 100
            msg += (f"\nBudget: Rp {trip['budget']:,} ({pct:.0f}% terpakai)"
                    f"\nSisa: Rp {left:,} {'✅' if left >= 0 else '⚠️ over'}")

        msg += "\n\n**Per kategori**\n"
        for c in summary['by_category']:
            pct = c['total'] / summary['total'] * 100
            msg += f"• {c['name'] or 'Lainnya'}: Rp {c['total']:,} ({pct:.0f}%)\n"

        if verbose:
            msg += "\n**Pengeluaran**\n"
            for it in summary['items'][:15]:
                msg += f"• {it['date']} — {it['description'] or it['category']}: Rp {it['amount']:,}\n"
            if len(summary['items']) > 15:
                msg += f"…dan {len(summary['items']) - 15} lainnya\n"

        return msg

    @staticmethod
    def _trip_days(trip: Dict) -> int:
        """
        Days to divide the total by.

        For a finished trip that is its real length. For a running one it is the
        days elapsed so far, so the figure reads as an actual burn rate ("we are
        spending X per day") instead of being diluted by days that have not
        happened yet -- day one would otherwise report a fantasy average.
        """
        try:
            start = datetime.strptime(trip['start_date'], "%Y-%m-%d")
            if trip['status'] == 'done' and trip['end_date']:
                end = datetime.strptime(trip['end_date'], "%Y-%m-%d")
            else:
                end = datetime.now()
            return max((end - start).days + 1, 1)
        except Exception:
            return 0

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
• _Pengeluaran:_ "makan 40.000" / "jajan 25rb" / "ojek 25.000 gopay"
• _Pemasukan:_ "gajian 5jt" / "freelance 500rb"
• _Hutang:_ "hutang ke budi 100rb" / "budi hutang ke saya 50rb"

**Commands:**
• /balance - Balance bulan ini
• /expenses [bulan] - Pengeluaran per kategori (contoh: /expenses 2026-08)
• /trip - Ringkasan trip yang sedang berjalan
• /trip list - Daftar semua trip
• /trip mulai <nama> - Mulai trip baru
• /trip selesai - Tutup trip yang berjalan
• /debts - Semua hutang/piutang
• /debt [nama] - Hutang/piutang dengan teman tertentu
• /categories - Lihat daftar kategori
• /help - Bantuan ini

**Format Tanggal:** YYYY-MM-DD
**Format Uang:** 40000, 40.000, 40rb, 40ribu, 40k, 1jt, 2 juta

ℹ️ Selama trip aktif, semua pengeluaran otomatis masuk ke trip itu."""
