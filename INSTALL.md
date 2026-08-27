# Installation & Deployment Guide

Complete step-by-step guide untuk deploy Finance Tracker Dashboard di VPS dengan Nginx, systemd, dan Let's Encrypt SSL.

## Prerequisites

- **OS:** Ubuntu 22.04+ / Debian 12+
- **Python:** 3.9+
- **Root/sudo access**
- **Domain name** (dengan DNS sudah pointing ke VPS IP)
- **Nginx** installed

## 🚀 Quick Install (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/USER/finance-tracker-dashboard.git
cd finance-tracker-dashboard

# 2. Run installer
chmod +x install.sh
sudo ./install.sh

# Follow on-screen prompts untuk:
# - Domain name (default: finance.example.com)
# - Email untuk Let's Encrypt
# - Installation path (default: /home/ubuntu/finance-tracker)
```

Done! Dashboard accessible di `https://yourdomain.com/finance/`

---

## 📋 Manual Installation (Detailed)

### Step 1: Clone & Setup

```bash
git clone https://github.com/USER/finance-tracker-dashboard.git
cd finance-tracker-dashboard

# Create working directory
sudo mkdir -p /opt/finance-tracker
sudo cp -r . /opt/finance-tracker
cd /opt/finance-tracker
```

### Step 2: Install Dependencies

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install -y python3 python3-flask python3-flask-cors nginx certbot python3-certbot-nginx git
```

**Or via pip:**
```bash
pip3 install -r requirements.txt
```

### Step 3: Initialize Database

```bash
# Create & populate SQLite database
python3 << 'EOF'
from finance_tracker import FinanceTracker
tracker = FinanceTracker("/opt/finance-tracker/finance.db")
tracker.init_db()
print("✅ Database initialized")
EOF
```

### Step 4: Create Systemd Service

**Create `/etc/systemd/system/finance-dashboard.service`:**

```ini
[Unit]
Description=Finance Tracker Dashboard API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/finance-tracker
ExecStart=/usr/bin/python3 /opt/finance-tracker/api_server.py
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Enable & start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable finance-dashboard
sudo systemctl start finance-dashboard
sudo systemctl status finance-dashboard
```

### Step 5: Configure Nginx

**Create `/etc/nginx/sites-available/finance`:**

```nginx
# HTTP redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL (certbot will populate these)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Static dashboard
    location /finance/ {
        alias /var/www/finance/;
        try_files $uri $uri/ /finance/index.html;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # API proxy
    location /finance/api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/finance /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 6: Copy Dashboard Files

```bash
sudo mkdir -p /var/www/finance
sudo cp dashboard/index.html /var/www/finance/
sudo chown -R www-data:www-data /var/www/finance
```

### Step 7: Generate SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

Certbot otomatis:
- Generate certificate
- Update Nginx config
- Setup auto-renewal

**Verify:**
```bash
sudo certbot certificates
# Output shows expiry date & auto-renewal status
```

### Step 8: Verify Installation

```bash
# Check API health
curl -s https://yourdomain.com/finance/api/health | jq

# Check balance
curl -s https://yourdomain.com/finance/api/balance | jq

# Open in browser
open https://yourdomain.com/finance/
```

---

## 🔄 Integration with Hermes Agent (Optional)

Jika ingin track via WhatsApp:

### Setup Hermes Finance Tracker

```bash
# Copy finance tracker ke Hermes skills
cp -r . ~/.hermes/skills/productivity/finance-tracker-dashboard

# Reference di Hermes:
# User di WhatsApp bisa kirim: "jajan 25rb"
# Hermes auto-process via finance CLI
```

### WhatsApp Commands

```
jajan 25rb              → expense recorded
gajian 5jt              → income recorded
hutang ke budi 100rb    → debt tracked
balance                 → show balance
expenses                → breakdown by category
debts                   → all pending debts
```

---

## 🐳 Docker Deployment (Alternative)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python3", "api_server.py"]
```

**Build & run:**
```bash
docker build -t finance-tracker .
docker run -d -p 5000:5000 -v /data/finance.db:/app/finance.db finance-tracker
```

---

## 📊 Maintenance

### View Logs

```bash
# Real-time
sudo journalctl -u finance-dashboard -f

# Last 50 lines
sudo journalctl -u finance-dashboard -n 50

# Today's logs
sudo journalctl -u finance-dashboard --since today
```

### Backup Database

```bash
# Manual backup
cp /opt/finance-tracker/finance.db ~/backup/finance-$(date +%Y%m%d).db

# Automated (cron)
0 2 * * * cp /opt/finance-tracker/finance.db ~/backup/finance-$(date +\%Y\%m\%d).db
```

### Update Application

```bash
cd /opt/finance-tracker
git pull origin main

# Restart service
sudo systemctl restart finance-dashboard
```

### Monitor Service

```bash
# Status
sudo systemctl status finance-dashboard

# Resource usage
ps aux | grep finance-dashboard
top -p $(pgrep -f finance-dashboard)

# Check port
sudo netstat -tlnp | grep 5000
# or: ss -tlnp | grep 5000
```

---

## 🔒 Security Checklist

- ✅ HTTPS only (SSL certificate from Let's Encrypt)
- ✅ HTTP → HTTPS redirect (301)
- ✅ Auto SSL renewal (certbot.timer)
- ✅ Security headers (X-Frame-Options, etc)
- ✅ Database in secure location (not web-accessible)
- ✅ Systemd service runs as non-root (www-data)
- ✅ File permissions: 644 (files), 755 (dirs)

### Additional Security (Optional)

```bash
# Add basic auth (if needed)
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd your_username

# Then in Nginx location block:
# auth_basic "Finance Dashboard";
# auth_basic_user_file /etc/nginx/.htpasswd;

# Firewall (UFW)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## ❌ Troubleshooting

### Service won't start
```bash
sudo systemctl status finance-dashboard
sudo journalctl -u finance-dashboard -n 20

# Common: Python import error
python3 -c "import flask; import flask_cors"
```

### 502 Bad Gateway (Nginx)
```bash
# Check API server running
curl http://127.0.0.1:5000/api/health

# Check Nginx config
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### Dashboard shows "API error"
```bash
# Check CORS headers
curl -i https://yourdomain.com/finance/api/health

# Check database exists
ls -la /opt/finance-tracker/finance.db

# Check file permissions
ls -la /var/www/finance/
```

### SSL certificate issues
```bash
# Check expiry
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal

# Troubleshoot renewal
sudo certbot renew --dry-run
```

---

## 📞 Support

- Issues: Create GitHub issue
- Docs: See README.md
- API: See api_server.py comments

---

## 🎯 Next Steps

1. **Add data** via CLI or WhatsApp
2. **Check dashboard** at `https://yourdomain.com/finance/`
3. **Setup backup** routine
4. **Monitor logs** regularly
5. **Update regularly** via `git pull`

Happy tracking! 💰
