"""Test the /chat endpoint with web search enabled."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

BASE = "http://127.0.0.1:5000"

# Clear context first
requests.post(f"{BASE}/clear_context")

# Send a web search query
print("Sending web search query...")
resp = requests.post(f"{BASE}/chat", json={
    "message": "What is quantum computing?",
    "web_search": True
}, timeout=60)

data = resp.json()
print(f"\nStatus: {resp.status_code}")

if "sources" in data:
    print(f"\nSOURCES ({len(data['sources'])} found):")
    for i, s in enumerate(data["sources"]):
        print(f"  [{i+1}] {s['title']} - {s['url']}")

if "response" in data:
    print(f"\nRESPONSE (first 500 chars):")
    print(data["response"][:500])

if "error" in data:
    print(f"\nERROR: {data['error']}")

print("\nDone!")
