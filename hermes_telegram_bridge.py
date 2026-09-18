#!/usr/bin/env python3
"""
Hermes Telegram Finance Bridge
Routes Telegram messages directly to finance_cli.py
Designed for slash commands: /expenses, /income, /debts, /categories, /balance, /help
"""

import sys
import subprocess
import json
from pathlib import Path

FINANCE_CLI = Path(__file__).parent / "finance_cli.py"
FINANCE_DB = Path(__file__).parent / "finance.db"

def run_finance_command(command: str) -> str:
    """Execute finance CLI command and return formatted output"""
    try:
        result = subprocess.run(
            [sys.executable, str(FINANCE_CLI), command],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(Path(__file__).parent)
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return f"❌ Error: {error}"
    
    except subprocess.TimeoutExpired:
        return "❌ Command timeout"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def handle_message(text: str) -> str:
    """
    Handle incoming Telegram message
    Routes to appropriate CLI command
    """
    text = text.strip()
    
    if not text:
        return run_finance_command("/help")
    
    # Slash commands
    commands = ['/expenses', '/income', '/debts', '/balance', '/categories', '/help']
    
    if text in commands or text.split()[0] in commands:
        # Direct command execution
        return run_finance_command(text)
    
    # Natural language transaction input
    # Pass directly to CLI which handles parsing
    return run_finance_command(text)

def main():
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = sys.stdin.read().strip()
    
    response = handle_message(message)
    print(response)

if __name__ == "__main__":
    main()
