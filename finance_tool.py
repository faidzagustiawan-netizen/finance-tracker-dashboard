#!/usr/bin/env python3
"""
Hermes Finance Tracker Tool
Executable wrapper for Hermes tool system
"""

import sys
import json
import subprocess
from pathlib import Path

BRIDGE = Path(__file__).parent / "hermes_telegram_bridge.py"

def main():
    try:
        # Parse arguments
        if len(sys.argv) < 2:
            print(json.dumps({
                "status": "error",
                "message": "Missing command argument"
            }))
            sys.exit(1)
        
        command = sys.argv[1]
        
        # Execute via bridge
        result = subprocess.run(
            [sys.executable, str(BRIDGE), command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Output result
        output = {
            "status": "success" if result.returncode == 0 else "error",
            "result": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }
        
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(result.returncode)
    
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
