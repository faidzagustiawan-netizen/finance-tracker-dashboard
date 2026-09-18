#!/bin/bash
# Setup Finance Tracker untuk Hermes Integration

TRACKER_DIR="/home/ubuntu/finance-tracker"

echo "🚀 Finance Tracker Setup"
echo "========================"
echo ""

# Check if directory exists
if [ ! -d "$TRACKER_DIR" ]; then
    echo "❌ Tracker directory not found at $TRACKER_DIR"
    exit 1
fi

cd "$TRACKER_DIR"

# Initialize database
echo "📦 Initializing database..."
python3 << 'EOF'
import sqlite3
from pathlib import Path

db_path = "finance.db"
if not Path(db_path).exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema_path = Path("schema.sql")
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())
    
    conn.commit()
    conn.close()
    print("✅ Database created successfully")
else:
    print("✅ Database already exists")
EOF

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📝 Usage:"
echo "  From CLI: python3 finance_cli.py 'jajan 25rb'"
echo "  From Hermes: hermes chat -q 'jajan 25rb' (if hooked)"
echo ""
echo "📚 Documentation: cat README.md"
echo "🆘 Help: python3 finance_cli.py '/help'"
