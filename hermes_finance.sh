#!/bin/bash
# Hermes Finance Tracker CLI Wrapper
# Direct pass-through to finance_cli.py with proper output formatting

cd /home/ubuntu/finance-tracker

if [ $# -eq 0 ]; then
    python3 finance_cli.py "/help"
    exit 0
fi

# Join all arguments into a single command
COMMAND="$@"

# Execute and capture output
OUTPUT=$(python3 finance_cli.py "$COMMAND" 2>&1)
EXIT_CODE=$?

echo "$OUTPUT"
exit $EXIT_CODE
