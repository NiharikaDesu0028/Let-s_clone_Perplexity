from google import genai
import os

API_KEY = "AIzaSyAhXf5A4pqav__eQt6eknUsmEpgltNF-rY"
client = genai.Client(api_key=API_KEY)

models_to_try = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash"
]

for m in models_to_try:
    print(f"Testing {m}...")
    try:
        response = client.models.generate_content(
            model=m,
            contents="hi"
        )
        print(f"  SUCCESS: {m}")
        break
    except Exception as e:
        print(f"  FAILED: {m} - {e}")
