#!/usr/bin/env python3
"""
Telegram Bot for Finance Tracker
Lightweight alternative to WhatsApp for transaction recording
"""

import os
import sys
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from finance_tracker import FinanceTracker
from command_handler import FinanceCommandHandler

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Hardcoded allowed user (backup if env parsing fails)
ALLOWED_USER_ID = 1928502167

class TelegramFinanceBot:
    def __init__(self, token: str, allowed_users: list = None):
        """
        Initialize Telegram bot
        token: Bot token dari BotFather
        allowed_users: List of allowed Telegram user IDs
        """
        self.token = token
        self.allowed_users = allowed_users or []
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.tracker = FinanceTracker()
        self.cmd_handler = FinanceCommandHandler()  # Uses default db_path
        self.offset = 0
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown"):
        """Send message to Telegram"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            response = requests.post(f"{self.api_url}/sendMessage", json=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def send_inline_keyboard(self, chat_id: int, text: str, buttons: list):
        """Send message with inline keyboard buttons"""
        try:
            reply_markup = {
                'inline_keyboard': buttons
            }
            data = {
                'chat_id': chat_id,
                'text': text,
                'reply_markup': reply_markup,
                'parse_mode': 'Markdown'
            }
            response = requests.post(f"{self.api_url}/sendMessage", json=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"Error sending keyboard: {e}")
            return None
    
    def get_updates(self):
        """Get new updates from Telegram"""
        try:
            params = {'offset': self.offset, 'timeout': 30}
            response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=35)
            return response.json()
        except Exception as e:
            print(f"Error getting updates: {e}")
            return {'ok': False, 'result': []}
    
    def handle_message(self, message: dict):
        """Handle incoming message"""
        chat_id = message.get('chat', {}).get('id')
        user_id = message.get('from', {}).get('id')
        text = message.get('text', '').strip()
        
        print(f"[LOG] Received: user_id={user_id}, text='{text}', allowed={self.allowed_users}")
        
        # Check allowed users
        if self.allowed_users and user_id not in self.allowed_users:
            msg = f"❌ Tidak authorized. User ID: {user_id}"
            print(f"[LOG] REJECT: {msg}")
            self.send_message(chat_id, msg)
            return
        
        print(f"[LOG] ACCEPT: Processing message")
        
        # Handle commands
        if text.startswith('/'):
            response = self.handle_command(text, user_id)
        else:
            # Natural language transaction input
            response = self.handle_transaction(text, user_id)
        
        # Send response
        if isinstance(response, str):
            self.send_message(chat_id, response)
        elif isinstance(response, dict) and response.get('buttons'):
            self.send_inline_keyboard(chat_id, response['text'], response['buttons'])
    
    def handle_command(self, text: str, user_id: int) -> str:
        """Handle / commands"""
        parts = text.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command == '/start':
            return """
🎯 *Finance Tracker Bot*

Perintah tersedia:
• `/balance` - Lihat balance
• `/expenses` - Lihat pengeluaran
• `/income` - Lihat pemasukan
• `/debts` - Lihat semua hutang
• `/categories` - Lihat kategori
• `/help` - Bantuan

*Atau ketik langsung:*
`makan 50rb cash` - Catat expense
`gajian 5jt bri` - Catat income
`hutang ke budi 100rb` - Catat hutang
            """
        elif command == '/balance':
            balance = self.tracker.get_balance()
            return f"""
💰 *Balance*

Balance: Rp {balance['balance']:,}
Pemasukan: Rp {balance['income']:,}
Pengeluaran: Rp {balance['expense']:,}
            """
        elif command == '/expenses':
            expenses = self.tracker.get_expenses(limit=5)
            text = "📊 *5 Pengeluaran Terakhir*\n\n"
            for exp in expenses:
                text += f"• {exp['description']} - Rp {exp['amount']:,}\n"
            text += "\n💡 Tip: `/expenses 2026-08` untuk bulan lain"
            return text
        elif command == '/income':
            income = self.tracker.get_income(limit=5)
            text = "💵 *5 Pemasukan Terakhir*\n\n"
            for inc in income:
                text += f"• {inc['description']} - Rp {inc['amount']:,}\n"
            return text
        elif command == '/debts':
            debts = self.tracker.get_debts()
            if not debts:
                return "✅ Tidak ada hutang"
            text = "🤝 *Hutang & Piutang*\n\n"
            for debt in debts:
                status = "Hutang" if debt['type'] == 'owed' else "Piutang"
                text += f"• {debt['friend_name']}: Rp {debt['amount']:,} ({status})\n"
            return text
        elif command == '/help':
            return self.cmd_handler.cmd_help()
        else:
            # Delegate anything this thin wrapper does not know (e.g. /trip) to
            # the shared command handler, so the bot and the CLI always agree
            # on what exists instead of drifting apart.
            return self.cmd_handler.handle_message(text)
    
    def handle_transaction(self, text: str, user_id: int) -> str:
        """Handle natural language transaction"""
        if not text:
            return "⏳ Ketik transaksi atau /help"
        
        # Use command handler
        response = self.cmd_handler.handle_message(text, force=False)
        
        if isinstance(response, dict) and response.get('action') == 'confirm':
            return response.get('message', 'Confirm?')
        
        return response or "❌ Format tidak dikenal. Ketik /help"
    
    def start_polling(self):
        """Start polling for updates"""
        print("🤖 Telegram Finance Bot started (polling mode)")
        print(f"Bot API: {self.api_url}")
        
        while True:
            try:
                updates = self.get_updates()
                
                if updates.get('ok'):
                    for update in updates.get('result', []):
                        self.offset = update['update_id'] + 1
                        
                        if 'message' in update:
                            self.handle_message(update['message'])
                
            except KeyboardInterrupt:
                print("\n✅ Bot stopped")
                break
            except Exception as e:
                print(f"Error in polling loop: {e}")
                import time
                time.sleep(5)

# CLI interface
if __name__ == '__main__':
    # Load from .env or command line
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    allowed_user_str = os.getenv('ALLOWED_USER_ID', '')
    
    # Parse command line args if provided
    if len(sys.argv) > 1:
        token = sys.argv[1]
        allowed_users = [int(uid) for uid in sys.argv[2:]]
    else:
        # Parse from env, fallback to hardcoded
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN not found in .env or command line")
            sys.exit(1)
        
        allowed_users = []
        if allowed_user_str:
            try:
                allowed_users = [int(uid.strip()) for uid in allowed_user_str.split(',')]
            except ValueError:
                print("⚠️ Invalid ALLOWED_USER_ID format in .env, using hardcoded")
                allowed_users = [ALLOWED_USER_ID]
        else:
            # Use hardcoded as fallback
            allowed_users = [ALLOWED_USER_ID]
    
    print(f"🤖 Starting Telegram Finance Bot...")
    print(f"📱 Token: {token[:20]}...")
    print(f"👤 Allowed users: {allowed_users if allowed_users else 'All'}")
    
    bot = TelegramFinanceBot(token, allowed_users)
    bot.start_polling()
