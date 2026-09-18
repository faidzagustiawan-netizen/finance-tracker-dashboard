import requests
import json

TOKEN = "8992165745:AAGMqxvzSAhzHOn3v5TdyZ4vAI27Xe6vaOs"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Test getMe
resp = requests.get(f"{API_URL}/getMe")
print("Bot info:", resp.json())

# Test getUpdates
resp = requests.get(f"{API_URL}/getUpdates")
print("\nRecent updates:")
data = resp.json()
if data.get('result'):
    for update in data['result'][-5:]:
        print(json.dumps(update, indent=2))
else:
    print("No updates yet")
