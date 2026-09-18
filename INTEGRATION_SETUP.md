# 🚀 Finance Tracker - WhatsApp Integration Setup

**Status:** ✅ Skill created & webhook ready

Panduan setup untuk mengaktifkan `/finance` command di WhatsApp melalui Hermes.

---

## 📋 What's Already Done

✅ Finance tracker built dan tested
✅ Hermes skill `finance-tracker` created
✅ Webhook script ready (`hermes_webhook.py`)
✅ Database pre-initialized

---

## 🔧 Integration Methods

Ada 2 cara untuk mengaktifkan `/finance` command:

### **Method 1: Via Hermes Webhook (Recommended)**

Hermes supports webhook triggers. Kita bisa setup agar `/finance` command auto-trigger ke finance tracker.

**Steps:**

1. **Setup webhook in Hermes config**
   ```bash
   hermes webhook subscribe finance-command
   ```

2. **Configure the webhook**
   Edit `~/.hermes/config.yaml`:
   ```yaml
   webhooks:
     - name: finance-command
       trigger: message_contains
       pattern: "^/finance"
       action: execute_script
       script: /home/ubuntu/finance-tracker/hermes_webhook.py
       platform: whatsapp
   ```

3. **Restart gateway**
   ```bash
   hermes gateway restart
   ```

4. **Test dari WhatsApp**
   ```
   /finance jajan 25rb
   ```

---

### **Method 2: Via Hermes Slash Command Handler**

Hermes punya built-in slash command system. Bisa leverage itu.

**Setup:**

1. **Check if slash commands enabled**
   ```bash
   hermes config get display.slash_commands
   ```

2. **Create custom slash command hook**
   Edit atau create file: `~/.hermes/custom-commands.yaml`
   ```yaml
   commands:
     finance:
       description: "Finance tracking"
       script: /home/ubuntu/finance-tracker/hermes_webhook.py
       platforms: [whatsapp]
   ```

3. **Restart & test**
   ```bash
   hermes gateway restart
   ```

---

### **Method 3: Simple - Direct CLI (No Automation)**

Jika webhook terlalu kompleks, bisa tetap pakai CLI langsung:

```bash
# Terminal
cd /home/ubuntu/finance-tracker
python3 finance_cli.py "jajan 25rb"
python3 finance_cli.py "/balance"
```

---

## 🧪 Testing Without Webhook

Test webhook script langsung:

```bash
# Test CLI mode
python3 /home/ubuntu/finance-tracker/hermes_webhook.py "jajan 25rb"

# Test webhook mode (JSON)
echo '{"message": "/finance jajan 25rb", "sender": "62895397133738", "platform": "whatsapp"}' \
  | python3 /home/ubuntu/finance-tracker/hermes_webhook.py
```

---

## 📖 Usage After Setup

Once webhook activated, dari WhatsApp:

```
/finance jajan 25rb
Response: ✅ Pengeluaran dicatat: Rp 25,000 (Makanan)

/finance gajian 5jt
Response: ✅ Pemasukan dicatat: Rp 5,000,000 (Gaji)

/finance hutang ke budi 100rb
Response: ✅ Hutang ke Budi: Rp 100,000

/finance /balance
Response: 💰 BALANCE BULAN INI
          Pemasukan: Rp 5,000,000
          Pengeluaran: Rp 25,000
          ─────────────
          Balance: Rp 4,975,000 ✅

/finance /debts
Response: 💳 HUTANG/PIUTANG PENDING
          • Saya HUTANG ke Budi: Rp 100,000
          ─────────────
          Total hutang saya: Rp 100,000
```

---

## 🎯 Recommended Approach

**For your setup (Baileys WhatsApp bridge):**

Gunakan **Method 1 (Webhook)** karena:
- Native Hermes support
- Automatic message routing
- No manual intervention needed
- Already compatible dengan WhatsApp gateway

---

## 🔍 Troubleshooting

**Q: `/finance` command tidak di-recognize**
A: Pastikan gateway sudah di-restart setelah setup

**Q: Response lambat**
A: Check database size: `ls -lh finance.db`

**Q: Error "script not found"**
A: Verify path: `ls -l /home/ubuntu/finance-tracker/hermes_webhook.py`

**Q: WhatsApp tidak connect**
A: Check gateway status: `hermes gateway status`

---

## 📁 Files for Integration

```
/home/ubuntu/finance-tracker/
├── hermes_webhook.py      ← Webhook handler (baru)
├── command_handler.py     ← Command parser
├── finance_tracker.py     ← Core logic
├── finance.db             ← Database
├── finance_cli.py         ← CLI interface
└── INTEGRATION_SETUP.md   ← File ini
```

---

## ⚡ Quick Setup (Copy-Paste)

```bash
# 1. Verify webhook script exists
ls -l /home/ubuntu/finance-tracker/hermes_webhook.py

# 2. Test it works
python3 /home/ubuntu/finance-tracker/hermes_webhook.py "jajan 25rb"

# 3. Check Hermes config
hermes config show | grep webhook

# 4. Add webhook config to ~/.hermes/config.yaml
# (Manual - depends on Hermes version)

# 5. Restart gateway
# Note: May need to do from different terminal if gateway running
```

---

## 📞 Next Steps

1. **Choose integration method** (recommend Method 1)
2. **Setup webhook** in Hermes config
3. **Restart gateway**
4. **Test from WhatsApp** with `/finance jajan 25rb`
5. **Start tracking!**

---

**Status:** Ready to integrate  
**Location:** `/home/ubuntu/finance-tracker/`  
**Test Command:** `python3 hermes_webhook.py "jajan 25rb"`
