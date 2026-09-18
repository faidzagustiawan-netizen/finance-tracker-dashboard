#!/usr/bin/env python3
"""
Hermes Finance Tracker Integration
Hook ini bisa dipanggil dari WhatsApp via Hermes

Integrasi: Tambahkan ke webhook atau cron job Hermes
"""

import sys
import os
from pathlib import Path

# Setup path
tracker_dir = Path(__file__).parent
sys.path.insert(0, str(tracker_dir))

from command_handler import FinanceCommandHandler

def process_message(text: str) -> str:
    """Process finance message dari WhatsApp/chat"""
    db_path = tracker_dir / "finance.db"
    handler = FinanceCommandHandler(str(db_path))
    return handler.handle_message(text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: hermes_finance.py '<message>'")
        print("Example: hermes_finance.py 'jajan 25rb'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    result = process_message(message)
    print(result)
