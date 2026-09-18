#!/usr/bin/env python3
"""
Hermes Finance Tracker Skill Integration
Gunakan command: hermes chat -q "25rb makanan"
Atau dari WhatsApp: "25rb makanan"
"""

import sys
import os
from pathlib import Path

# Add finance tracker ke path
tracker_dir = Path(__file__).parent
sys.path.insert(0, str(tracker_dir))

from command_handler import FinanceCommandHandler

def process_finance_message(text: str) -> str:
    """
    Main entry point untuk Hermes integration
    """
    db_path = tracker_dir / "finance.db"
    handler = FinanceCommandHandler(str(db_path))
    response = handler.handle_message(text)
    return response

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 hermes_finance.py '<message>'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    result = process_finance_message(message)
    print(result)
