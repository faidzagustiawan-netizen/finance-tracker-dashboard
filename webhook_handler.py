"""
Hermes Finance Tracker Webhook Handler
Receives Telegram messages and routes to finance CLI
"""

import json
import subprocess
import sys
from pathlib import Path

BRIDGE_SCRIPT = Path(__file__).parent / "hermes_telegram_bridge.py"

def handle_finance_request(message: str) -> dict:
    """
    Handle finance tracker request from Telegram
    Returns JSON response for Hermes
    """
    try:
        result = subprocess.run(
            [sys.executable, str(BRIDGE_SCRIPT), message],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        response_text = result.stdout.strip() or result.stderr.strip()
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "message": response_text,
            "code": result.returncode
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)}",
            "code": 500
        }

# This function is called by Hermes webhook
def process_webhook(event: dict) -> dict:
    """Process incoming webhook from Telegram"""
    try:
        message = event.get("message", "").strip()
        
        if not message:
            return {
                "reply": "Gunakan format: /expenses, /income, /debts, /categories, /balance, atau ketik natural language (contoh: jajan 25rb)"
            }
        
        result = handle_finance_request(message)
        
        return {
            "reply": result["message"],
            "status": result["status"]
        }
    
    except Exception as e:
        return {
            "reply": f"Error: {str(e)}",
            "status": "error"
        }

if __name__ == "__main__":
    # Test mode
    if len(sys.argv) > 1:
        test_message = " ".join(sys.argv[1:])
        result = handle_finance_request(test_message)
        print(json.dumps(result, indent=2))
