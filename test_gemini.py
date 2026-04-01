from google import genai
import sys

try:
    client = genai.Client(api_key="AIzaSyAhXf5A4pqav__eQt6eknUsmEpgltNF-rY")
    print("Attempting to generate content with gemini-2.0-flash...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Hello! Say 'This is Gemini 2.0 Flash speaking!'"
    )
    print("Response received:")
    print(response.text)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {str(e)}")
    sys.exit(1)
