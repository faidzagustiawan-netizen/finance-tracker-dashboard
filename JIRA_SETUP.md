# Jira Integration Setup Guide

## 🔗 Quick Start

Connect Finance Tracker ke Jira untuk auto-create issues, track bugs, dan sync data.

---

## 📋 Step 1: Get Jira API Token

1. Login ke Jira Cloud (https://your-domain.atlassian.net)
2. Click profile → Settings → Security → API tokens
3. Click "Create API token"
4. Give it name: "Finance Tracker Bot"
5. Copy token (jangan di-share!)

**Format:** `ATATT3xFfGF1234567890...` (panjang)

---

## 🔑 Step 2: Get Project Key

1. Open Jira project
2. Click Settings (gear icon)
3. Look for "Project key" (contoh: `FIN`, `TRACK`, `FINANCE`)
4. Or see in URL: `https://company.atlassian.net/browse/FIN-123` → key adalah `FIN`

---

## 📝 Step 3: Create Config File

Create file: `/home/ubuntu/.jira/config.json`

```bash
mkdir -p /home/ubuntu/.jira
nano /home/ubuntu/.jira/config.json
```

Isi dengan:

```json
{
  "domain": "your-domain.atlassian.net",
  "email": "your-email@company.com",
  "api_token": "ATATT3xFfGF1234567890...",
  "project_key": "FIN"
}
```

Ganti dengan data kamu, terus save (Ctrl+X → Y → Enter)

---

## 🧪 Step 4: Test Connection

```bash
cd /home/ubuntu/finance-tracker
python3 jira_client.py test your-domain.atlassian.net your-email@company.com YOUR_API_TOKEN YOUR_PROJECT_KEY
```

Contoh:
```bash
python3 jira_client.py test mycompany.atlassian.net john@company.com ATATT3xFfGF1234567890 FIN
```

Expected output:
```
✅ Connected to Jira
   User: John Doe (john@company.com)
```

---

## 🎯 Usage Examples

### Create Issue

```bash
python3 jira_client.py create \
  mycompany.atlassian.net \
  john@company.com \
  ATATT3xFfGF1234567890 \
  FIN \
  "Balance calculation error on 2026-09-03" \
  "System calculated -Rp 55,000 but should be different. Please investigate."
```

### Search Issues

```bash
python3 jira_client.py search \
  mycompany.atlassian.net \
  john@company.com \
  ATATT3xFfGF1234567890 \
  FIN \
  "project = FIN AND status = Open"
```

### Add Comment

```bash
python3 jira_client.py comment \
  mycompany.atlassian.net \
  john@company.com \
  ATATT3xFfGF1234567890 \
  FIN-123 \
  "Fixed in latest deployment"
```

---

## 🔐 Security Notes

- API token = sensitive! Keep it safe
- Don't commit token to Git
- Use environment variables untuk production:
  ```bash
  export JIRA_TOKEN="your_token"
  export JIRA_EMAIL="your_email@company.com"
  ```

---

## 📊 Integration dengan Finance Tracker

Bisa auto-create issues untuk:
- Large transactions (> Rp 1,000,000)
- Balance anomalies
- Missing transaction records
- System errors

Example: Buat cron job untuk daily issues

```bash
# /home/ubuntu/finance-tracker/sync_to_jira.sh
#!/bin/bash
python3 /home/ubuntu/finance-tracker/jira_client.py create \
  $(cat /home/ubuntu/.jira/config.json | jq -r '.domain') \
  $(cat /home/ubuntu/.jira/config.json | jq -r '.email') \
  $(cat /home/ubuntu/.jira/config.json | jq -r '.api_token') \
  $(cat /home/ubuntu/.jira/config.json | jq -r '.project_key') \
  "Daily Finance Summary - $(date +%Y-%m-%d)" \
  "Balance: Rp -55,000 | Transactions: 2"
```

---

## ✅ Status

After setup:
- Jira client ready
- Config file created
- Connection tested
- Ready for automation!

Next: Setup cron job untuk auto-sync?
