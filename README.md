# 💰 Finance Tracker Dashboard

Personal finance tracker with WhatsApp integration, CLI, SQLite storage, and a beautiful web dashboard. Built for VPS deployment behind Nginx with Let's Encrypt SSL.

## ✨ Features

- **Natural Language Input** — Track expenses/income/debts with plain Indonesian text
  - `jajan 25rb` → expense recorded (Makanan)
  - `gajian dari nfd 10 juta` → income recorded (Gaji)
  - `hutang ke budi 100rb` → debt tracked
- **Smart Auto-Categorization** — 7 expense + 4 income categories, keyword-matched
- **Debt Tracking** — Track money owed to/from friends, net balance calculation
- **Web Dashboard** — Charts (Chart.js), balance cards, transaction history, auto-refresh
- **REST API** — Flask backend serving JSON from SQLite
- **WhatsApp Integration** — Works with [Hermes Agent](https://github.com/NousResearch/hermes-agent) gateway

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/USER/finance-tracker-dashboard.git
cd finance-tracker-dashboard

# 2. Install dependencies
sudo apt install -y python3 python3-flask python3-flask-cors
# or: pip3 install -r requirements.txt

# 3. Initialize database
python3 -c "from finance_tracker import FinanceTracker; FinanceTracker()"

# 4. Test it
python3 finance_cli.py "jajan 25rb"
python3 finance_cli.py "/balance"

# 5. Start API server
python3 api_server.py
# → http://localhost:5000/api/balance
```

## 🌐 Web Dashboard Deployment

See [INSTALL.md](INSTALL.md) for full Nginx + systemd + HTTPS setup guide.

**Architecture:**

```
Browser → https://yourdomain.com/finance/
              ↓
         Nginx (reverse proxy)
         ├─ /finance/      → static HTML dashboard
         └─ /finance/api/  → Flask API (port 5000)
              ↓
         SQLite database
```

## 📡 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/balance` | Current balance (income − expense) |
| `GET /api/expenses?month=YYYY-MM` | Expenses by category |
| `GET /api/transactions?limit=50&type=expense` | Recent transactions |
| `GET /api/debts` | All pending debts |
| `GET /api/debts/<friend>` | Debt detail per friend |
| `GET /api/summary` | Complete financial summary |
| `GET /api/stats` | Financial statistics |

## 💬 Usage Examples

```bash
# CLI
python3 finance_cli.py "bensin 50rb"
python3 finance_cli.py "gajian 5jt"
python3 finance_cli.py "hutang ke budi 100rb makan bareng"
python3 finance_cli.py "budi hutang ke saya 50rb"
python3 finance_cli.py "/balance"
python3 finance_cli.py "/expenses"
python3 finance_cli.py "/debts"
python3 finance_cli.py "/debt budi"
```

## 📁 Structure

```
finance-tracker-dashboard/
├── finance_tracker.py       # Core DB logic (SQLite)
├── command_handler.py       # Natural language parser
├── finance_cli.py           # CLI entry point
├── api_server.py            # Flask REST API
├── dashboard/
│   └── index.html           # Web dashboard (Chart.js)
├── schema.sql               # Database schema
├── finance-dashboard.service # Systemd unit
├── nginx-finance.conf       # Nginx config template
├── install.sh               # Automated installer
└── requirements.txt
```

## 🔧 Tech Stack

- **Backend:** Python 3, Flask, SQLite
- **Frontend:** Vanilla JS, Chart.js, dark theme CSS
- **Server:** systemd, Nginx, Let's Encrypt (certbot)
- **Integration:** WhatsApp via Hermes Agent (optional)

## 📝 License

MIT License — see [LICENSE](LICENSE)

## 🙏 Credits

Built as part of a personal AI agent setup with [Hermes Agent](https://hermes-agent.nousresearch.com) and CasaOS.
