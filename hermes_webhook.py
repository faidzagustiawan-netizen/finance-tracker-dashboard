#!/usr/bin/env python3
"""
Hermes Finance Tracker Webhook
Automatically process /finance commands dari WhatsApp

Setup:
1. This script di-call oleh Hermes gateway when message matches /finance
2. Parse message dan process via finance tracker
3. Return response ke WhatsApp
"""

import sys
import json
from pathlib import Path

# Setup path
tracker_dir = Path(__file__).parent
sys.path.insert(0, str(tracker_dir))

from command_handler import FinanceCommandHandler

def process_webhook(payload: dict) -> dict:
    """
    Process webhook from Hermes gateway
    
    Input payload:
    {
        "message": "/finance jajan 25rb",
        "sender": "62895397133738",
        "platform": "whatsapp",
        "timestamp": "2026-08-27T23:52:00Z"
    }
    
    Returns:
    {
        "response": "✅ Pengeluaran dicatat: Rp 25,000 (Makanan)",
        "status": "success"
    }
    """
    
    try:
        message = payload.get("message", "").strip()
        
        # Remove /finance prefix if present
        if message.startswith("/finance"):
            message = message[8:].strip()
        
        if not message:
            return {
                "response": "❌ Pesan kosong. Contoh: /finance jajan 25rb",
                "status": "error"
            }
        
        # Process via finance tracker
        db_path = tracker_dir / "finance.db"
        handler = FinanceCommandHandler(str(db_path))
        response = handler.handle_message(message)
        
        return {
            "response": response,
            "status": "success"
        }
    
    except Exception as e:
        return {
            "response": f"❌ Error: {str(e)}",
            "status": "error"
        }

def main():
    """Entry point for webhook processing"""
    if len(sys.argv) > 1:
        # Command line mode (for testing)
        message = " ".join(sys.argv[1:])
        db_path = tracker_dir / "finance.db"
        handler = FinanceCommandHandler(str(db_path))
        response = handler.handle_message(message)
        print(response)
    else:
        # Webhook mode (from stdin)
        try:
            payload = json.loads(sys.stdin.read())
            result = process_webhook(payload)
            print(json.dumps(result))
        except Exception as e:
            print(json.dumps({
                "response": f"❌ Invalid webhook: {str(e)}",
                "status": "error"
            }))

if __name__ == "__main__":
    main()
