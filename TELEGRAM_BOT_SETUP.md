# Telegram Finance Bot Setup Guide

## 🤖 Quick Start

Telegram bot untuk Finance Tracker adalah alternatif lightweight ke WhatsApp. Token usage jauh lebih efisien!

---

## 📋 Step 1: Get Telegram Bot Token

1. Open Telegram, cari `@BotFather`
2. Kirim `/start`
3. Kirim `/newbot`
4. Pilih nama bot (contoh: `FinanceTrackerBot`)
5. Pilih username (harus unik, contoh: `@faidz_finance_bot`)
6. Copy token yang diberikan (format: `123456789:ABCDEFGhijklmnop...`)

**Simpan token di tempat aman!**

---

## 📱 Step 2: Get Your Telegram User ID

1. Open Telegram, cari `@userinfobot`
2. Kirim `/start`
3. Bot akan reply dengan user ID kamu (contoh: `987654321`)

**Catat user ID ini!**

---

## 🔧 Step 3: Configure Service

Update `/etc/systemd/system/telegram-finance-bot.service`:

```bash
sudo nano /etc/systemd/system/telegram-finance-bot.service
```

Ganti:
- `TOKEN_PLACEHOLDER` → bot token dari step 1
- `USER_ID` → user ID dari step 2

Contoh:
```
ExecStart=/usr/bin/python3 /home/ubuntu/finance-tracker/telegram_bot.py 123456789:ABCDEFGhijklmnop 987654321
```

Save (Ctrl+X → Y → Enter)

---

## 🚀 Step 4: Start Bot

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start bot
sudo systemctl start telegram-finance-bot

# Enable auto-start on reboot
sudo systemctl enable telegram-finance-bot

# Check status
sudo systemctl status telegram-finance-bot

# View logs
sudo journalctl -u telegram-finance-bot -f
```

---

## 💬 Usage

Open Telegram, find your bot (`@faidz_finance_bot`), send:

### Commands:
```
/start      - Intro & help
/balance    - Lihat balance
/expenses   - 5 pengeluaran terakhir
/income     - 5 pemasukan terakhir
/debts      - Lihat semua hutang
/categories - Lihat kategori
/help       - Bantuan lengkap
```

### Transaction Input:
```
makan 50rb cash         → Expense: Rp 50,000 (Makanan, Cash)
gajian 5jt bri          → Income: Rp 5,000,000 (Gaji, BRI)
hutang ke budi 100rb    → Debt: Rp 100,000 (ke Budi)
bayar listrik 200rb spay → Expense: Rp 200,000 (Tagihan, SPay)
```

---

## 📊 Comparison: WhatsApp vs Telegram

| Aspect | WhatsApp | Telegram |
|--------|----------|----------|
| Token per message | 11-15K | 200-500 |
| Response time | Slower | Faster |
| Setup complexity | Complex | Simple |
| Inline buttons | No | Yes ✅ |
| Log/history | Limited | Full |
| Polling overhead | High | Low |
| Cost efficiency | ❌ Brutal | ✅ Great |

**Telegram is 20-50x more token-efficient!**

---

## 🔐 Security Notes

- Bot token = sensitive! Keep it safe
- User ID list = who can use bot
- Add multiple users if needed (space-separated):
  ```
  ExecStart=... TOKEN user_id_1 user_id_2 user_id_3
  ```
- Logs stored in `/var/log/telegram-finance-bot.log`

---

## ⚠️ Troubleshooting

**Bot not responding:**
```bash
sudo systemctl restart telegram-finance-bot
sudo journalctl -u telegram-finance-bot -n 50
```

**Permission errors:**
```bash
sudo chown ubuntu:ubuntu /home/ubuntu/finance-tracker/telegram_bot.py
```

**Token invalid:**
- Check token from @BotFather (no spaces, exact copy)
- Restart bot: `sudo systemctl restart telegram-finance-bot`

**User not authorized:**
- Check user ID is correct
- Add to allowed list if needed

---

## 📈 Next: Optimize Further

1. **CLI wrapper** for even faster input:
   ```bash
   alias finance="python3 /home/ubuntu/finance-tracker/finance_cli.py"
   finance "makan 50rb cash"
   ```

2. **Dashboard alerts** - Cron job kirim daily summary via Telegram

3. **Batch processing** - Multiple transactions in one message

---

## ✅ Status

After setup:
- Telegram bot running 24/7
- Token-efficient transaction recording
- Quick balance checks
- No WhatsApp token bloat!

Happy tracking! 🎉
