from google import genai
import os

API_KEY = "AIzaSyAhXf5A4pqav__eQt6eknUsmEpgltNF-rY"
try:
    client = genai.Client(api_key=API_KEY)
    print("Available Models:")
    for model in client.models.list():
        print(f"- {model.name}")
except Exception as e:
    print(f"Error: {e}")
