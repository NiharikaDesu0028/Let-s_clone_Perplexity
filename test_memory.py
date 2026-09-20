import requests
import json

BASE_URL = "http://localhost:5000"

def test_memory():
    # 1. Clear context
    requests.post(f"{BASE_URL}/clear_context")
    print("Context cleared.")

    # 2. Tell the AI a name
    payload1 = {"message": "My name is Gowtham. Remember this."}
    response1 = requests.post(f"{BASE_URL}/chat", json=payload1)
    print(f"User: {payload1['message']}")
    print(f"AI: {response1.json().get('response')}")

    # 3. Ask the AI the name
    payload2 = {"message": "What is my name?"}
    response2 = requests.post(f"{BASE_URL}/chat", json=payload2)
    print(f"User: {payload2['message']}")
    print(f"AI: {response2.json().get('response')}")

if __name__ == "__main__":
    test_memory()
