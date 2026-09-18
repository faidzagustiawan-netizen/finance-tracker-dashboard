#!/usr/bin/env python3
"""
Hermes Finance Tracker Command
Slash command handler for /finance, /expenses, /income, /debts, etc.
"""

import sys
import subprocess
from pathlib import Path

FINANCE_CLI = Path("/home/ubuntu/finance-tracker/finance_cli.py")

def main():
    if len(sys.argv) < 2:
        cmd = "/help"
    else:
        cmd = " ".join(sys.argv[1:])
    
    try:
        result = subprocess.run(
            ["python3", str(FINANCE_CLI), cmd],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(FINANCE_CLI.parent)
        )
        print(result.stdout)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
