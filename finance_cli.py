#!/usr/bin/env python3
"""
CLI untuk Finance Tracker
Penggunaan: python3 finance_cli.py "25rb makanan"
"""
import sys
from command_handler import FinanceCommandHandler

def main():
    if len(sys.argv) < 2:
        handler = FinanceCommandHandler("/home/ubuntu/finance-tracker/finance.db")
        print(handler.cmd_help())
        return
    
    text = " ".join(sys.argv[1:])
    handler = FinanceCommandHandler("/home/ubuntu/finance-tracker/finance.db")
    response = handler.handle_message(text)
    print(response)

if __name__ == "__main__":
    main()
