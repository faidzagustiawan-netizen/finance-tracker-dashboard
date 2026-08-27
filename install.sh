#!/bin/bash
# Finance Tracker Dashboard - Automated Installer
# Usage: sudo ./install.sh

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  💰 Finance Tracker Dashboard - Installer                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
  echo "❌ This script must be run as root (sudo ./install.sh)"
  exit 1
fi

# Detect OS
if ! command -v apt-get &> /dev/null; then
  echo "❌ This installer supports Debian/Ubuntu only"
  exit 1
fi

# Configuration
read -p "📍 Domain name (default: finance.example.com): " DOMAIN
DOMAIN=${DOMAIN:-finance.example.com}

read -p "📧 Email for Let's Encrypt (default: admin@example.com): " EMAIL
EMAIL=${EMAIL:-admin@example.com}

read -p "📁 Installation path (default: /opt/finance-tracker): " INSTALL_PATH
INSTALL_PATH=${INSTALL_PATH:-/opt/finance-tracker}

read -p "👤 Service user (default: www-data): " SERVICE_USER
SERVICE_USER=${SERVICE_USER:-www-data}

echo ""
echo "Configuration:"
echo "  Domain: $DOMAIN"
echo "  Email: $EMAIL"
echo "  Path: $INSTALL_PATH"
echo "  User: $SERVICE_USER"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 1
fi

echo ""
echo "▶ Step 1: Update system packages..."
apt-get update -qq
apt-get upgrade -y -qq

echo "▶ Step 2: Install dependencies..."
apt-get install -y -qq python3 python3-flask python3-flask-cors \
  nginx certbot python3-certbot-nginx git curl

echo "▶ Step 3: Create installation directory..."
mkdir -p "$INSTALL_PATH"
cd "$INSTALL_PATH"

# If running in git repo, copy files
if [ -f "finance_tracker.py" ]; then
  echo "✅ Files already in place"
else
  echo "❌ finance_tracker.py not found in current directory"
  exit 1
fi

echo "▶ Step 4: Initialize database..."
python3 << 'PYEOF'
from finance_tracker import FinanceTracker
import os

db_path = os.path.join(os.getcwd(), "finance.db")
tracker = FinanceTracker(db_path)
tracker.init_db()
print(f"✅ Database initialized: {db_path}")
PYEOF

echo "▶ Step 5: Setup dashboard files..."
sudo mkdir -p /var/www/finance
sudo cp dashboard/index.html /var/www/finance/
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" /var/www/finance
echo "✅ Dashboard files copied to /var/www/finance"

echo "▶ Step 6: Create systemd service..."
sudo tee /etc/systemd/system/finance-dashboard.service > /dev/null << EOF
[Unit]
Description=Finance Tracker Dashboard API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_PATH
ExecStart=/usr/bin/python3 $INSTALL_PATH/api_server.py
Restart=always
RestartSec=10s
StartLimitInterval=60s
StartLimitBurst=5
StandardOutput=journal
StandardError=journal

Environment="PYTHONUNBUFFERED=1"
Environment="FLASK_ENV=production"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable finance-dashboard
sudo systemctl start finance-dashboard
sleep 2

if sudo systemctl is-active --quiet finance-dashboard; then
  echo "✅ Systemd service started"
else
  echo "⚠️  Service may not have started. Check: sudo journalctl -u finance-dashboard"
fi

echo "▶ Step 7: Configure Nginx..."
sudo tee /etc/nginx/sites-available/finance > /dev/null << 'NGINXEOF'
# HTTP redirect
server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

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
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location /finance/ {
        alias /var/www/finance/;
        try_files $uri $uri/ /finance/index.html;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    location /finance/api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

# Replace domain placeholder
sudo sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /etc/nginx/sites-available/finance

# Enable site
sudo ln -sf /etc/nginx/sites-available/finance /etc/nginx/sites-enabled/

# Test config
if sudo nginx -t 2>&1 | grep -q "successful"; then
  echo "✅ Nginx configured"
else
  echo "❌ Nginx config error"
  exit 1
fi

sudo systemctl reload nginx

echo "▶ Step 8: Generate SSL certificate..."
if sudo certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --non-interactive 2>&1 | grep -q "Successfully"; then
  echo "✅ SSL certificate generated"
else
  echo "⚠️  SSL certificate generation may have issues"
  echo "   Manual retry: sudo certbot --nginx -d $DOMAIN"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Installation Complete!                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Dashboard: https://$DOMAIN/finance/"
echo "🔌 API Health: https://$DOMAIN/finance/api/health"
echo ""
echo "📋 Next steps:"
echo "   1. Test API: curl https://$DOMAIN/finance/api/balance"
echo "   2. Add data: python3 $INSTALL_PATH/finance_cli.py \"jajan 25rb\""
echo "   3. View dashboard in browser"
echo ""
echo "📖 Documentation: See INSTALL.md & README.md"
echo "📝 Logs: sudo journalctl -u finance-dashboard -f"
echo ""
